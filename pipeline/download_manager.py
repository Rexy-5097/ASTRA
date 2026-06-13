#!/usr/bin/env python3
"""Download and preprocess Phase 6 ASTRA targets."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.phase6_utils import (
    DEFAULT_PHASE6_ROOT,
    MANIFEST_COLUMNS,
    REJECTED_COLUMNS,
    append_csv_row,
    ensure_phase6_structure,
    normalize_tic_id,
    parse_jsonish_list,
    read_csv_rows,
    tic_dir_name,
    utc_now,
    write_csv_rows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("download_manager")

MAX_DOWNLOAD_RETRIES = 2
RETRY_BACKOFF_BASE = 5


def _manifest_path(data_root: Path, requested: Path | None) -> Path:
    if requested:
        return requested
    return data_root / "catalogs" / "usable_manifest.csv"


def _row_is_processable(row: dict[str, str], allow_pending_tess: bool) -> bool:
    status = (row.get("rejection_status") or "").strip()
    if not status:
        return True
    return allow_pending_tess and status == "pending_tess_check"


def _existing_successes(processed_root: Path) -> set[str]:
    successes = set()
    for meta_path in processed_root.glob("TIC_*/metadata.json"):
        try:
            metadata = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        tic = normalize_tic_id(metadata.get("tic_id"))
        if tic and metadata.get("selected_period") is not None:
            successes.add(tic)
    return successes


def _float_or_none(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    text = normalize_tic_id(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _cleanup_failed_target(data_root: Path, tic_id: Any) -> None:
    tic = normalize_tic_id(tic_id)
    if not tic:
        return
    star_dir = data_root / "processed" / tic_dir_name(tic)
    if star_dir.exists():
        shutil.rmtree(star_dir)


def _process_row(data_root: Path, row: dict[str, str], max_sectors: int, force: bool) -> dict[str, Any]:
    from pipeline.preprocess import process_star

    tic_id = _int_or_none(row.get("tic_id"))
    astra_class = row.get("astra_class", "")
    catalog_period = _float_or_none(row.get("catalog_period"))
    ra = _float_or_none(row.get("ra"))
    dec = _float_or_none(row.get("dec"))
    source_catalogs = parse_jsonish_list(row.get("source_catalogs"))

    last_result: dict[str, Any] = {}
    for attempt in range(1 + MAX_DOWNLOAD_RETRIES):
        result = process_star(
            tic_id=tic_id,
            astra_class=astra_class,
            output_dir=data_root / "processed",
            max_sectors=max_sectors,
            search_name=row.get("name") or None,
            ra=ra,
            dec=dec,
            force=force,
            catalog_period=catalog_period,
            source_catalogs=source_catalogs,
            primary_source=row.get("primary_source") or None,
            catalog_label=row.get("catalog_label") or None,
            duplicate_group_id=row.get("duplicate_group_id") or None,
            catalog_row=row,
            raw_output_dir=data_root / "raw",
        )
        if "error" not in result:
            out_row = dict(row)
            out_row["tic_id"] = normalize_tic_id(result.get("tic_id", row.get("tic_id")))
            out_row["tess_available"] = "true"
            out_row["crossmatch_status"] = "processed"
            out_row["rejection_status"] = ""
            return {
                "status": "success",
                "row": out_row,
                "metadata": result,
            }

        last_result = result
        if result.get("stage") not in {"download"}:
            break
        if attempt < MAX_DOWNLOAD_RETRIES:
            time.sleep(RETRY_BACKOFF_BASE * (3 ** attempt))

    _cleanup_failed_target(data_root, tic_id)
    return {
        "status": "failed",
        "row": row,
        "error": last_result.get("error", "unknown"),
        "stage": last_result.get("stage", "unknown"),
        "tic_id": normalize_tic_id(last_result.get("tic_id", row.get("tic_id"))),
    }


def _write_event(data_root: Path, event: dict[str, Any]) -> None:
    path = data_root / "logs" / "download_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fp:
        fp.write(json.dumps(event, sort_keys=True, default=str) + "\n")


def download_phase6(
    data_root: Path = DEFAULT_PHASE6_ROOT,
    manifest: Path | None = None,
    max_usable: int = 1000,
    workers: int = 2,
    max_sectors: int = 8,
    force: bool = False,
    allow_pending_tess: bool = False,
    allow_partial_gate: bool = False,
) -> dict[str, Any]:
    data_root = ensure_phase6_structure(data_root)
    manifest_path = _manifest_path(data_root, manifest)
    rows = read_csv_rows(manifest_path)
    if not rows:
        log.warning("No rows found in manifest: %s", manifest_path)
    processed_root = data_root / "processed"
    existing = _existing_successes(processed_root)

    queue: list[dict[str, str]] = []
    for row in rows:
        tic = normalize_tic_id(row.get("tic_id"))
        if tic and tic in existing and not force:
            continue
        if not _row_is_processable(row, allow_pending_tess=allow_pending_tess):
            continue
        queue.append(row)

    remaining = max(0, max_usable - len(existing))
    queue = queue[:remaining]
    available_total = len(existing) + len(queue)
    if not allow_partial_gate and available_total < max_usable:
        msg = (
            f"Refusing to start downloads for gate {max_usable}: "
            f"only {available_total} usable or already processed rows are available."
        )
        log.error(msg)
        return {
            "manifest": str(manifest_path),
            "existing_successes": len(existing),
            "queued": 0,
            "successes": 0,
            "failures": 0,
            "error": msg,
        }

    log.info("Loaded %d rows from %s", len(rows), manifest_path)
    log.info("Existing usable processed samples: %d", len(existing))
    log.info("Queued rows: %d", len(queue))

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    if not queue:
        return {
            "manifest": str(manifest_path),
            "existing_successes": len(existing),
            "queued": 0,
            "successes": 0,
            "failures": 0,
        }

    effective_workers = max(1, min(workers, len(queue)))
    with ThreadPoolExecutor(max_workers=effective_workers) as pool:
        futures = {
            pool.submit(_process_row, data_root, row, max_sectors, force): row
            for row in queue
        }
        for future in as_completed(futures):
            result = future.result()
            event = {
                "timestamp": utc_now(),
                "status": result["status"],
                "tic_id": result.get("tic_id") or result.get("row", {}).get("tic_id"),
                "astra_class": result.get("row", {}).get("astra_class"),
                "stage": result.get("stage", ""),
                "error": result.get("error", ""),
            }
            _write_event(data_root, event)

            if result["status"] == "success":
                successes.append(result["row"])
                log.info("Processed TIC %s (%s)", result["row"].get("tic_id"), result["row"].get("astra_class"))
            else:
                failures.append(result)
                row = result["row"]
                append_csv_row(
                    data_root / "rejected" / "rejected_samples.csv",
                    {
                        "timestamp": utc_now(),
                        "tic_id": result.get("tic_id") or row.get("tic_id"),
                        "name": row.get("name", ""),
                        "astra_class": row.get("astra_class", ""),
                        "stage": result.get("stage", "unknown"),
                        "reason": result.get("error", "unknown"),
                        "source_catalogs": row.get("source_catalogs", ""),
                        "primary_source": row.get("primary_source", ""),
                    },
                    REJECTED_COLUMNS,
                )
                log.warning("Rejected TIC %s at %s: %s", row.get("tic_id"), result.get("stage"), result.get("error"))

    processed_manifest = data_root / "catalogs" / "processed_manifest.csv"
    previous_successes = read_csv_rows(processed_manifest)
    seen = {normalize_tic_id(row.get("tic_id")) for row in previous_successes}
    combined = previous_successes + [row for row in successes if normalize_tic_id(row.get("tic_id")) not in seen]
    write_csv_rows(processed_manifest, combined, MANIFEST_COLUMNS)

    summary = {
        "manifest": str(manifest_path),
        "existing_successes": len(existing),
        "queued": len(queue),
        "successes": len(successes),
        "failures": len(failures),
        "processed_manifest": str(processed_manifest),
    }
    log.info("Download manager summary: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and preprocess ASTRA Phase 6 targets")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--max-usable", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-sectors", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict-manifest", action="store_true",
                        help="Deprecated. Strict manifest processing is now the default.")
    parser.add_argument("--allow-pending-tess", action="store_true",
                        help="Development override. Process rows still marked pending_tess_check.")
    parser.add_argument("--allow-partial-gate", action="store_true",
                        help="Development override. Start downloads even if manifest cannot satisfy max-usable.")
    args = parser.parse_args()

    summary = download_phase6(
        data_root=args.data_root,
        manifest=args.manifest,
        max_usable=args.max_usable,
        workers=args.workers,
        max_sectors=args.max_sectors,
        force=args.force,
        allow_pending_tess=args.allow_pending_tess,
        allow_partial_gate=args.allow_partial_gate,
    )
    if summary.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
