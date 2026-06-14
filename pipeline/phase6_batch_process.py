#!/usr/bin/env python3
"""
ASTRA — phase6_batch_process.py

Batch processor for Phase 6 dataset expansion.
Reads from usable_manifest.csv and outputs to data/phase6/processed/.

Features:
    • Reads from Phase 6 usable_manifest.csv (NOT catalog_full.json)
    • Outputs to data/phase6/processed/ and data/phase6/raw/
    • Passes all manifest metadata (name, ra, dec, period, sources) to preprocess.py
    • Configurable per-class limits for staged processing
    • Resume-safe caching (skips existing processed stars)
    • Retry logic with exponential backoff
    • Checkpoint reports at configurable intervals
    • Download-quality metrics collection

Usage:
    # Pilot: 40 per class, 3 workers
    python pipeline/phase6_batch_process.py --per-class 40 --workers 3

    # Stage B: 100 per class, 6 workers
    python pipeline/phase6_batch_process.py --per-class 100 --workers 6

    # Full: all usable, 6 workers
    python pipeline/phase6_batch_process.py --workers 6
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import multiprocessing as mp
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("phase6_batch")

# Paths
DATA_DIR = PROJECT_ROOT / "data"
PHASE6_ROOT = DATA_DIR / "phase6"
MANIFEST_PATH = PHASE6_ROOT / "catalogs" / "usable_manifest.csv"
OUTPUT_DIR = PHASE6_ROOT / "processed"
RAW_DIR = PHASE6_ROOT / "raw"
LOG_DIR = PHASE6_ROOT / "logs"
REPORT_DIR = PHASE6_ROOT / "audits"

# Retry config
MAX_DOWNLOAD_RETRIES = 2
RETRY_BACKOFF_BASE = 5

# Required output files per star
REQUIRED_FILES = [
    "flux_1000.npy", "flux_200.npy",
    "folded_flux_1000.npy", "folded_flux_200.npy",
    "metadata.json",
]


def _is_already_processed(tic_id: str, name: str, output_dir: Path) -> bool:
    """Check if a star has already been processed."""
    if tic_id:
        star_dir = output_dir / f"TIC_{tic_id}"
        if star_dir.is_dir() and all((star_dir / f).exists() for f in REQUIRED_FILES):
            return True
    return False


def _process_one_star(args_tuple: tuple) -> dict:
    """Process a single star from manifest row. Designed for multiprocessing."""
    (row_json, output_dir_str, raw_dir_str, max_sectors) = args_tuple
    row = json.loads(row_json)
    output_dir = Path(output_dir_str)
    raw_dir = Path(raw_dir_str)

    from pipeline.phase6_utils import normalize_tic_id, parse_jsonish_list
    from pipeline.preprocess import process_star

    tic_raw = normalize_tic_id(row.get("tic_id"))
    tic_id = int(tic_raw) if tic_raw else None
    astra_class = row.get("astra_class", "")
    search_name = row.get("name", "").strip() or None
    if search_name == "TIC":
        search_name = None

    try:
        ra = float(row.get("ra", "")) if row.get("ra", "").strip() else None
    except (ValueError, TypeError):
        ra = None
    try:
        dec = float(row.get("dec", "")) if row.get("dec", "").strip() else None
    except (ValueError, TypeError):
        dec = None
    try:
        catalog_period = float(row.get("catalog_period", "")) if row.get("catalog_period", "").strip() else None
    except (ValueError, TypeError):
        catalog_period = None

    source_catalogs = parse_jsonish_list(row.get("source_catalogs", ""))
    primary_source = row.get("primary_source", "")

    identifier = f"TIC {tic_id}" if tic_id else (search_name or f"({ra},{dec})")

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
            force=False,
            catalog_period=catalog_period,
            source_catalogs=source_catalogs,
            primary_source=primary_source,
            catalog_label=row.get("catalog_label", ""),
            catalog_row=row,
            raw_output_dir=raw_dir,
        )
        if "error" not in result:
            return {
                "tic_id": result.get("tic_id", tic_id),
                "name": search_name or "",
                "astra_class": astra_class,
                "status": "success",
                "n_sectors": result.get("n_sectors", 0),
                "n_points_raw": result.get("n_points_raw", 0),
                "n_points_clean": result.get("n_points_clean", 0),
                "cadence_type": result.get("cadence_type", ""),
                "period_source": result.get("period_source", ""),
                "selected_period": result.get("selected_period"),
                "snr_estimate": result.get("snr_estimate"),
                "variability_amplitude": result.get("variability_amplitude"),
            }

        last_result = result
        if result.get("stage") != "download":
            break

        if attempt < MAX_DOWNLOAD_RETRIES:
            wait = RETRY_BACKOFF_BASE * (3 ** attempt)
            time.sleep(wait)

    return {
        "tic_id": last_result.get("tic_id", tic_id),
        "name": search_name or "",
        "astra_class": astra_class,
        "status": "failed",
        "error": last_result.get("error", "unknown"),
        "stage": last_result.get("stage", "unknown"),
    }


def _load_manifest(per_class: int | None = None) -> list[dict]:
    """Load and optionally limit the usable manifest."""
    if not MANIFEST_PATH.exists():
        log.error("Manifest not found: %s", MANIFEST_PATH)
        sys.exit(1)

    with open(MANIFEST_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    log.info("Loaded manifest: %d rows", len(rows))

    if per_class is not None:
        counts: dict[str, int] = defaultdict(int)
        limited: list[dict] = []
        for row in rows:
            cls = row.get("astra_class", "")
            if cls in CLASS_NAMES and counts[cls] < per_class:
                counts[cls] += 1
                limited.append(row)
        rows = limited
        log.info("Limited to %d per class: %d total", per_class, len(rows))

    return rows


def phase6_batch_process(
    per_class: int | None = None,
    workers: int = 3,
    max_sectors: int = 8,
    checkpoint_interval: int = 50,
) -> Path:
    """Process Phase 6 stars from usable_manifest.csv."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows = _load_manifest(per_class=per_class)

    # Filter out already-processed
    to_process: list[dict] = []
    skipped: list[dict] = []
    for row in manifest_rows:
        tic = row.get("tic_id", "").strip()
        name = row.get("name", "").strip()
        if _is_already_processed(tic, name, OUTPUT_DIR):
            skipped.append(row)
        else:
            to_process.append(row)

    skipped_by_class = Counter(r["astra_class"] for r in skipped)
    log.info("To process: %d (skipping %d cached)", len(to_process), len(skipped))

    if not to_process:
        log.info("Nothing to process!")
        report_path = _write_final_report([], skipped_by_class, per_class, workers)
        return report_path

    # Build work items (serialize rows as JSON for multiprocessing)
    work_items = [
        (json.dumps(row), str(OUTPUT_DIR), str(RAW_DIR), max_sectors)
        for row in to_process
    ]

    # Process
    results: list[dict] = []
    effective_workers = min(workers, len(work_items))
    start_time = time.time()

    if effective_workers <= 1:
        log.info("Processing %d stars sequentially…", len(work_items))
        for i, item in enumerate(work_items):
            r = _process_one_star(item)
            results.append(r)
            status = "✓" if r["status"] == "success" else "✗"
            log.info("[%d/%d] %s (%s) %s",
                     i + 1, len(work_items),
                     r.get("tic_id") or r.get("name", "?"),
                     r["astra_class"], status)

            # Checkpoint
            if (i + 1) % checkpoint_interval == 0:
                _write_checkpoint(results, i + 1, len(work_items), start_time)
    else:
        log.info("Processing %d stars with %d workers…",
                 len(work_items), effective_workers)
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=effective_workers) as pool:
            for i, r in enumerate(
                pool.imap_unordered(_process_one_star, work_items)
            ):
                results.append(r)
                status = "✓" if r["status"] == "success" else "✗"
                log.info("[%d/%d] %s (%s) %s",
                         i + 1, len(work_items),
                         r.get("tic_id") or r.get("name", "?"),
                         r["astra_class"], status)

                if (i + 1) % checkpoint_interval == 0:
                    _write_checkpoint(results, i + 1, len(work_items), start_time)

    elapsed = time.time() - start_time
    log.info("=" * 60)
    log.info("Phase 6 Batch Processing Complete (%.1fs)", elapsed)
    log.info("=" * 60)

    report_path = _write_final_report(results, skipped_by_class, per_class, workers)
    return report_path


def _write_checkpoint(results: list[dict], processed: int, total: int, start_time: float) -> None:
    """Write a progress checkpoint."""
    elapsed = time.time() - start_time
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    success_by_class = Counter(r["astra_class"] for r in success)
    failed_by_class = Counter(r["astra_class"] for r in failed)

    checkpoint = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processed": processed,
        "total": total,
        "elapsed_seconds": round(elapsed, 1),
        "success_count": len(success),
        "failed_count": len(failed),
        "success_by_class": dict(success_by_class),
        "failed_by_class": dict(failed_by_class),
        "success_rate": round(len(success) / processed * 100, 1) if processed > 0 else 0,
    }

    path = LOG_DIR / f"checkpoint_{processed:04d}.json"
    path.write_text(json.dumps(checkpoint, indent=2))
    log.info("Checkpoint %d/%d → %s (%.1f%% success)",
             processed, total, path.name, checkpoint["success_rate"])


def _write_final_report(
    results: list[dict],
    skipped_by_class: Counter,
    per_class: int | None,
    workers: int,
) -> Path:
    """Write the final processing report."""
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    success_by_class = Counter(r["astra_class"] for r in success)
    failed_by_class = Counter(r["astra_class"] for r in failed)

    # Download quality metrics
    sectors = [r.get("n_sectors", 0) for r in success if r.get("n_sectors")]
    points_raw = [r.get("n_points_raw", 0) for r in success if r.get("n_points_raw")]
    points_clean = [r.get("n_points_clean", 0) for r in success if r.get("n_points_clean")]
    snrs = [r.get("snr_estimate", 0) for r in success if r.get("snr_estimate")]
    cadence_dist = Counter(r.get("cadence_type", "unknown") for r in success)
    period_source_dist = Counter(r.get("period_source", "unknown") for r in success)

    # Failure analysis
    failure_stages = Counter(r.get("stage", "unknown") for r in failed)
    failure_reasons = Counter(r.get("error", "unknown")[:80] for r in failed)

    import numpy as np

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "per_class": per_class,
            "workers": workers,
        },
        "counts": {
            "total_processed": len(results),
            "success": len(success),
            "failed": len(failed),
            "skipped_cached": sum(skipped_by_class.values()),
            "success_rate_pct": round(len(success) / len(results) * 100, 1) if results else 0,
        },
        "success_by_class": dict(success_by_class),
        "failed_by_class": dict(failed_by_class),
        "skipped_by_class": dict(skipped_by_class),
        "download_quality": {
            "median_sectors": float(np.median(sectors)) if sectors else 0,
            "mean_sectors": float(np.mean(sectors)) if sectors else 0,
            "min_sectors": int(min(sectors)) if sectors else 0,
            "max_sectors": int(max(sectors)) if sectors else 0,
            "median_points_raw": float(np.median(points_raw)) if points_raw else 0,
            "median_points_clean": float(np.median(points_clean)) if points_clean else 0,
            "median_snr": float(np.median(snrs)) if snrs else 0,
            "cadence_distribution": dict(cadence_dist),
            "period_source_distribution": dict(period_source_dist),
        },
        "failures": {
            "by_stage": dict(failure_stages),
            "top_reasons": dict(failure_reasons.most_common(10)),
            "details": [
                {
                    "tic_id": r.get("tic_id"),
                    "name": r.get("name"),
                    "class": r["astra_class"],
                    "stage": r.get("stage"),
                    "error": r.get("error"),
                }
                for r in failed
            ],
        },
    }

    report_path = REPORT_DIR / "phase6_processing_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    log.info("Report → %s", report_path)

    # Summary log
    log.info("Success: %d | Failed: %d | Cached: %d",
             len(success), len(failed), sum(skipped_by_class.values()))
    for cls in CLASS_NAMES:
        log.info("  %-20s ok=%d fail=%d skip=%d",
                 cls, success_by_class.get(cls, 0),
                 failed_by_class.get(cls, 0),
                 skipped_by_class.get(cls, 0))

    if failed:
        log.warning("Failed stars:")
        for r in failed[:20]:
            log.warning("  %s (%s): %s [%s]",
                        r.get("tic_id") or r.get("name", "?"),
                        r["astra_class"],
                        r.get("error", "?")[:60],
                        r.get("stage", "?"))

    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ASTRA Phase 6 — Batch process from usable_manifest.csv"
    )
    parser.add_argument("--per-class", type=int, default=None,
                        help="Max stars per class (default: all)")
    parser.add_argument("--workers", type=int, default=3,
                        help="Parallel workers (default: 3)")
    parser.add_argument("--max-sectors", type=int, default=8,
                        help="Max TESS sectors per star (default: 8)")
    parser.add_argument("--checkpoint-interval", type=int, default=50,
                        help="Write checkpoint every N stars (default: 50)")
    args = parser.parse_args()

    phase6_batch_process(
        per_class=args.per_class,
        workers=args.workers,
        max_sectors=args.max_sectors,
        checkpoint_interval=args.checkpoint_interval,
    )
