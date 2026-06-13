#!/usr/bin/env python3
"""
ASTRA — batch_process.py  (v2 — multiprocessing support)

Process all stars in the catalog through the preprocessing pipeline.

Features:
    • Multiprocessing with configurable workers (default: 4)
    • Resume-safe caching — skips stars with existing valid outputs
    • Retry logic with exponential backoff for download failures
    • Per-class filtering and progress tracking
    • Detailed processing report saved to data/processing_report.json

Usage:
    python pipeline/batch_process.py                    # full run, 4 workers
    python pipeline/batch_process.py --workers 6        # 6 parallel workers
    python pipeline/batch_process.py --force             # reprocess all
    python pipeline/batch_process.py --max-stars 10     # quick test
    python pipeline/batch_process.py --class-name cepheid
"""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Project-root bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("batch_process")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR     = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog_full.json"
OUTPUT_DIR   = DATA_DIR / "processed"
REPORT_PATH  = DATA_DIR / "processing_report.json"

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
MAX_DOWNLOAD_RETRIES = 2
RETRY_BACKOFF_BASE   = 5

# ---------------------------------------------------------------------------
# Required output files
# ---------------------------------------------------------------------------
REQUIRED_FILES = [
    "flux_1000.npy", "flux_200.npy",
    "folded_flux_1000.npy", "folded_flux_200.npy",
    "metadata.json",
]


def _is_already_processed(tic_id: int, output_dir: Path) -> bool:
    """Return True if the star directory contains all required files."""
    star_dir = output_dir / f"TIC_{tic_id}"
    if not star_dir.is_dir():
        return False
    return all((star_dir / f).exists() for f in REQUIRED_FILES)


def _process_one_star(args_tuple: tuple) -> dict:
    """Process a single star with retries. Designed for multiprocessing."""
    (tic_id, astra_class, output_dir_str, max_sectors,
     search_name, ra, dec, force, catalog_period) = args_tuple
    output_dir = Path(output_dir_str)

    # Import here so each worker has its own module state
    from pipeline.preprocess import process_star

    last_result: dict = {}
    for attempt in range(1 + MAX_DOWNLOAD_RETRIES):
        result = process_star(
            tic_id=tic_id,
            astra_class=astra_class,
            output_dir=output_dir,
            max_sectors=max_sectors,
            search_name=search_name,
            ra=ra,
            dec=dec,
            force=force,
            catalog_period=catalog_period,
        )
        if "error" not in result:
            return {"tic_id": result.get("tic_id", tic_id),
                    "astra_class": astra_class,
                    "status": "success"}

        last_result = result
        if result.get("stage") != "download":
            break  # Only retry download errors

        if attempt < MAX_DOWNLOAD_RETRIES:
            wait = RETRY_BACKOFF_BASE * (3 ** attempt)
            time.sleep(wait)

    return {
        "tic_id": last_result.get("tic_id", tic_id),
        "astra_class": astra_class,
        "status": "failed",
        "error": last_result.get("error", "unknown"),
        "stage": last_result.get("stage", "unknown"),
    }


def batch_process(
    force: bool = False,
    max_stars: int | None = None,
    class_name: str | None = None,
    workers: int = 6,
    max_sectors: int = 8,
) -> Path:
    """Process all catalog stars, optionally in parallel."""

    if not CATALOG_PATH.exists():
        log.error("Catalog not found at %s. Run build_catalog.py first.",
                  CATALOG_PATH)
        sys.exit(1)

    with open(CATALOG_PATH) as fp:
        catalog: list[dict] = json.load(fp)

    log.info("Loaded catalog: %d entries", len(catalog))

    # Filter
    if class_name:
        if class_name not in CLASS_NAMES:
            log.error("Unknown class '%s'", class_name)
            sys.exit(1)
        catalog = [e for e in catalog if e["astra_class"] == class_name]
        log.info("Filtered to class '%s': %d entries", class_name, len(catalog))

    if max_stars is not None and max_stars < len(catalog):
        catalog = catalog[:max_stars]
        log.info("Limited to %d stars", max_stars)

    # Skip already processed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    to_process: list[dict] = []
    skipped_count: dict[str, int] = {c: 0 for c in CLASS_NAMES}

    for entry in catalog:
        tic_id = entry.get("tic_id")
        cls = entry["astra_class"]
        if tic_id is not None and not force and _is_already_processed(tic_id, OUTPUT_DIR):
            skipped_count[cls] = skipped_count.get(cls, 0) + 1
        else:
            to_process.append(entry)

    total_skipped = sum(skipped_count.values())
    log.info("To process: %d (skipping %d already done)", len(to_process),
             total_skipped)

    if not to_process:
        log.info("Nothing to process!")
        # Still write report
        _write_report({c: 0 for c in CLASS_NAMES},
                      {c: 0 for c in CLASS_NAMES},
                      skipped_count, [], force, max_stars, class_name)
        return REPORT_PATH

    # Build work items
    work_items = [
        (e.get("tic_id"), e["astra_class"], str(OUTPUT_DIR), max_sectors,
         e.get("name"), e.get("ra"), e.get("dec"), force,
         e.get("period"))
        for e in to_process
    ]

    # Process
    results: list[dict] = []
    effective_workers = min(workers, len(work_items))

    if effective_workers <= 1:
        log.info("Processing %d stars sequentially…", len(work_items))
        for i, item in enumerate(work_items):
            r = _process_one_star(item)
            results.append(r)
            status = "✓" if r["status"] == "success" else "✗"
            log.info("[%d/%d] TIC %s (%s) %s",
                     i + 1, len(work_items), r["tic_id"],
                     r["astra_class"], status)
    else:
        log.info("Processing %d stars with %d workers…",
                 len(work_items), effective_workers)
        # Use spawn context for macOS safety
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=effective_workers) as pool:
            for i, r in enumerate(
                pool.imap_unordered(_process_one_star, work_items)
            ):
                results.append(r)
                status = "✓" if r["status"] == "success" else "✗"
                log.info("[%d/%d] TIC %s (%s) %s",
                         i + 1, len(work_items), r["tic_id"],
                         r["astra_class"], status)

    # Tally
    success_count: dict[str, int] = {c: 0 for c in CLASS_NAMES}
    failure_count: dict[str, int] = {c: 0 for c in CLASS_NAMES}
    failures: list[dict] = []

    for r in results:
        cls = r["astra_class"]
        if r["status"] == "success":
            success_count[cls] = success_count.get(cls, 0) + 1
        else:
            failure_count[cls] = failure_count.get(cls, 0) + 1
            failures.append(r)

    # Summary
    total_success = sum(success_count.values())
    total_failed  = sum(failure_count.values())

    log.info("=" * 60)
    log.info("ASTRA Batch Processing Complete")
    log.info("=" * 60)
    log.info("  Succeeded       : %d", total_success)
    log.info("  Failed          : %d", total_failed)
    log.info("  Skipped (cached): %d", total_skipped)
    log.info("-" * 40)
    for cls in CLASS_NAMES:
        log.info("  %-20s  ok=%d  fail=%d  skip=%d",
                 cls, success_count.get(cls, 0),
                 failure_count.get(cls, 0),
                 skipped_count.get(cls, 0))

    if failures:
        log.warning("-" * 40)
        log.warning("Failed TIC IDs:")
        for f in failures:
            log.warning("  TIC %s (%s): %s [stage=%s]",
                        f["tic_id"], f["astra_class"],
                        f.get("error", "?"), f.get("stage", "?"))

    _write_report(success_count, failure_count, skipped_count,
                  failures, force, max_stars, class_name)
    return REPORT_PATH


def _write_report(success_count, failure_count, skipped_count,
                   failures, force, max_stars, class_name):
    report = {
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "total_success":   sum(success_count.values()),
        "total_failed":    sum(failure_count.values()),
        "total_skipped":   sum(skipped_count.values()),
        "per_class": {
            cls: {
                "success": success_count.get(cls, 0),
                "failed":  failure_count.get(cls, 0),
                "skipped": skipped_count.get(cls, 0),
            }
            for cls in CLASS_NAMES
        },
        "failures": failures,
        "force":    force,
        "max_stars": max_stars,
        "class_name": class_name,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as fp:
        json.dump(report, fp, indent=2)
    log.info("Saved report → %s", REPORT_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ASTRA — Batch-process catalog stars",
    )
    parser.add_argument("--force", action="store_true",
                        help="Reprocess all stars")
    parser.add_argument("--max-stars", type=int, default=None,
                        help="Limit total stars to process")
    parser.add_argument("--class-name", type=str, default=None,
                        choices=CLASS_NAMES,
                        help="Process only this class")
    parser.add_argument("--workers", type=int, default=6,
                        help="Number of parallel workers (default: 6)")
    parser.add_argument("--max-sectors", type=int, default=8,
                        help="Max TESS sectors per star (default: 8)")
    args = parser.parse_args()

    batch_process(
        force=args.force,
        max_stars=args.max_stars,
        class_name=args.class_name,
        workers=args.workers,
        max_sectors=args.max_sectors,
    )
