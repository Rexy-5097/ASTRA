#!/usr/bin/env python3
"""Programmatic audits for ASTRA Phase 6 datasets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES
from pipeline.phase6_utils import (
    DEFAULT_PHASE6_ROOT,
    PHASE6_REQUIRED_METADATA,
    angular_separation_arcsec,
    ensure_phase6_structure,
    normalize_tic_id,
    read_csv_rows,
    sha256_file,
    utc_now,
)

ARRAY_SPECS = {
    "flux_1000.npy": (1000,),
    "flux_200.npy": (200,),
    "folded_flux_1000.npy": (1000,),
    "folded_flux_200.npy": (200,),
}


def _load_samples(data_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    samples: list[dict[str, Any]] = []
    errors: list[str] = []
    for star_dir in sorted((data_root / "processed").glob("TIC_*")):
        if not star_dir.is_dir():
            continue
        meta_path = star_dir / "metadata.json"
        if not meta_path.exists():
            errors.append(f"{star_dir.name}: missing metadata.json")
            continue
        try:
            metadata = json.loads(meta_path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{star_dir.name}: invalid metadata.json: {exc}")
            continue
        samples.append({"star_dir": star_dir, "metadata": metadata})
    return samples, errors


def _audit_arrays(samples: list[dict[str, Any]]) -> tuple[list[str], Counter]:
    errors: list[str] = []
    stats: Counter = Counter()
    for sample in samples:
        star_dir: Path = sample["star_dir"]
        metadata = sample["metadata"]
        selected_period = metadata.get("selected_period")
        for filename, shape in ARRAY_SPECS.items():
            path = star_dir / filename
            if not path.exists():
                errors.append(f"{star_dir.name}: missing {filename}")
                continue
            if filename.startswith("folded") and selected_period is None:
                errors.append(f"{star_dir.name}: folded array exists without selected_period")
            try:
                arr = np.load(path)
            except Exception as exc:
                errors.append(f"{star_dir.name}: cannot load {filename}: {exc}")
                continue
            if arr.shape != shape:
                errors.append(f"{star_dir.name}: {filename} shape {arr.shape}, expected {shape}")
            if not np.all(np.isfinite(arr)):
                errors.append(f"{star_dir.name}: {filename} contains NaN or Inf")
            std = float(arr.std())
            mean = float(arr.mean())
            if std > 0 and abs(mean) > 1e-4:
                errors.append(f"{star_dir.name}: {filename} mean {mean:.6g}, expected near 0")
            if std > 0 and abs(std - 1.0) > 1e-4:
                errors.append(f"{star_dir.name}: {filename} std {std:.6g}, expected near 1")
            stats[f"{filename}_ok"] += 1
    return errors, stats


def _audit_metadata(data_root: Path, samples: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for sample in samples:
        star_dir = sample["star_dir"]
        metadata = sample["metadata"]
        for key in PHASE6_REQUIRED_METADATA:
            if key not in metadata:
                errors.append(f"{star_dir.name}: missing metadata field {key}")
        if metadata.get("selected_period") != metadata.get("period"):
            errors.append(f"{star_dir.name}: deprecated period alias does not match selected_period")
        if metadata.get("period_source") not in {"catalog", "BLS"}:
            errors.append(f"{star_dir.name}: invalid period_source {metadata.get('period_source')!r}")
        processed_hashes = metadata.get("processed_file_hashes", {})
        if isinstance(processed_hashes, dict):
            for filename, expected_hash in processed_hashes.items():
                path = star_dir / filename
                if path.exists() and expected_hash and sha256_file(path) != expected_hash:
                    errors.append(f"{star_dir.name}: processed hash mismatch for {filename}")
        else:
            errors.append(f"{star_dir.name}: processed_file_hashes is not a dict")
        raw_hashes = metadata.get("raw_file_hashes", {})
        if isinstance(raw_hashes, dict) and raw_hashes:
            for filename, expected_hash in raw_hashes.items():
                raw_path = data_root / filename
                if not raw_path.exists():
                    errors.append(f"{star_dir.name}: missing raw hash file {filename}")
                elif expected_hash and expected_hash != "unavailable" and sha256_file(raw_path) != expected_hash:
                    errors.append(f"{star_dir.name}: raw hash mismatch for {filename}")
        else:
            errors.append(f"{star_dir.name}: raw_file_hashes is not a non-empty dict")
    return errors


def _class_counts(samples: list[dict[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for sample in samples:
        counts[sample["metadata"].get("astra_class", "unknown")] += 1
    return counts


def _duplicate_audit(samples: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    tic_seen: dict[str, str] = {}
    coordinate_pairs: list[tuple[str, str, float]] = []
    coords: list[tuple[str, float, float]] = []

    for sample in samples:
        star_dir = sample["star_dir"].name
        metadata = sample["metadata"]
        tic = normalize_tic_id(metadata.get("tic_id"))
        if tic:
            if tic in tic_seen:
                errors.append(f"duplicate TIC {tic}: {tic_seen[tic]} and {star_dir}")
            tic_seen[tic] = star_dir
        try:
            if metadata.get("ra") is not None and metadata.get("dec") is not None:
                coords.append((star_dir, float(metadata["ra"]), float(metadata["dec"])))
        except (TypeError, ValueError):
            errors.append(f"{star_dir}: invalid coordinates")

    for i, left in enumerate(coords):
        for right in coords[i + 1:]:
            sep = angular_separation_arcsec(left[1], left[2], right[1], right[2])
            if sep <= 2.0:
                coordinate_pairs.append((left[0], right[0], sep))
                errors.append(f"strict coordinate duplicate: {left[0]} and {right[0]} at {sep:.3f} arcsec")

    return errors, {
        "unique_tic_count": len(tic_seen),
        "coordinate_duplicate_pairs": coordinate_pairs,
    }


def _split_audit(
    data_root: Path,
    samples: list[dict[str, Any]],
    required: bool,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    split_dir = data_root / "splits"
    split_names = ("train", "val", "calibration", "test")
    split_ids: dict[str, set[str]] = {}

    for split in split_names:
        path = split_dir / f"{split}_ids.json"
        if not path.exists():
            if required:
                errors.append(f"missing split file {path}")
            split_ids[split] = set()
            continue
        try:
            split_ids[split] = set(json.loads(path.read_text()))
        except Exception as exc:
            errors.append(f"cannot read split file {path}: {exc}")
            split_ids[split] = set()

    for i, left_name in enumerate(split_names):
        for right_name in split_names[i + 1:]:
            overlap = split_ids[left_name] & split_ids[right_name]
            if overlap:
                errors.append(f"split overlap {left_name}/{right_name}: {sorted(overlap)[:10]}")

    known_ids = {sample["star_dir"].name for sample in samples}
    assigned = set().union(*split_ids.values()) if split_ids else set()
    unknown = assigned - known_ids
    if unknown:
        errors.append(f"splits reference missing processed IDs: {sorted(unknown)[:10]}")

    duplicate_group_to_split: dict[str, str] = {}
    metadata_by_id = {sample["star_dir"].name: sample["metadata"] for sample in samples}
    for split, ids in split_ids.items():
        for sample_id in ids:
            group = metadata_by_id.get(sample_id, {}).get("duplicate_group_id")
            if not group:
                continue
            if group in duplicate_group_to_split and duplicate_group_to_split[group] != split:
                errors.append(f"duplicate group {group} crosses splits")
            duplicate_group_to_split[group] = split

    return errors, {name: len(ids) for name, ids in split_ids.items()}


def _rejection_counts(data_root: Path) -> Counter:
    rows = read_csv_rows(data_root / "rejected" / "rejected_samples.csv")
    counts: Counter = Counter()
    for row in rows:
        key = row.get("stage") or row.get("reason") or "unknown"
        counts[key] += 1
    return counts


def _write_report(path: Path, title: str, status: str, lines: list[str]) -> None:
    content = [f"# {title}", "", f"Status: **{status}**", "", *lines, ""]
    path.write_text("\n".join(content))


def run_audit(data_root: Path = DEFAULT_PHASE6_ROOT, stage: int = 0) -> dict[str, Any]:
    data_root = ensure_phase6_structure(data_root)
    audits_dir = data_root / "audits"
    samples, load_errors = _load_samples(data_root)
    array_errors, array_stats = _audit_arrays(samples)
    metadata_errors = _audit_metadata(data_root, samples)
    duplicate_errors, duplicate_stats = _duplicate_audit(samples)
    split_dir = data_root / "splits"
    split_required = stage >= 5000 or any((split_dir / f"{name}_ids.json").exists() for name in ("train", "val", "calibration", "test"))
    split_errors, split_stats = _split_audit(data_root, samples, required=split_required)
    rejection_counts = _rejection_counts(data_root)
    counts = _class_counts(samples)

    target_per_class = stage // len(CLASS_NAMES) if stage else 0
    balance_errors: list[str] = []
    if target_per_class:
        for cls in CLASS_NAMES:
            if counts.get(cls, 0) < target_per_class:
                balance_errors.append(
                    f"{cls}: {counts.get(cls, 0)} samples, target {target_per_class}"
                )

    total_errors = (
        load_errors
        + array_errors
        + metadata_errors
        + duplicate_errors
        + split_errors
        + balance_errors
    )
    overall_status = "PASS" if not total_errors else "FAIL"

    _write_report(
        audits_dir / "dataset_audit.md",
        "ASTRA Phase 6 Dataset Audit",
        overall_status,
        [
            f"Generated: {utc_now()}",
            f"Processed sample count: {len(samples)}",
            f"Stage target: {stage or 'not set'}",
            f"Total errors: {len(total_errors)}",
            "",
            "## First Errors",
            *(f"- {err}" for err in total_errors[:50]),
        ],
    )

    _write_report(
        audits_dir / "class_balance_report.md",
        "Class Balance Report",
        "PASS" if not balance_errors else "FAIL",
        [
            f"Target per class: {target_per_class or 'not set'}",
            "",
            *[f"- {cls}: {counts.get(cls, 0)}" for cls in CLASS_NAMES],
            "",
            *[f"- {err}" for err in balance_errors],
        ],
    )

    _write_report(
        audits_dir / "duplicate_audit.md",
        "Duplicate Audit",
        "PASS" if not duplicate_errors else "FAIL",
        [
            f"Unique TIC count: {duplicate_stats['unique_tic_count']}",
            f"Strict coordinate duplicate pairs: {len(duplicate_stats['coordinate_duplicate_pairs'])}",
            "",
            *(f"- {err}" for err in duplicate_errors[:50]),
        ],
    )

    _write_report(
        audits_dir / "preprocessing_consistency_report.md",
        "Preprocessing Consistency Report",
        "PASS" if not (array_errors or metadata_errors or load_errors) else "FAIL",
        [
            f"Array checks completed: {sum(array_stats.values())}",
            f"Load errors: {len(load_errors)}",
            f"Array errors: {len(array_errors)}",
            f"Metadata errors: {len(metadata_errors)}",
            "",
            *(f"- {err}" for err in (load_errors + array_errors + metadata_errors)[:50]),
        ],
    )

    _write_report(
        audits_dir / "corruption_recovery_report.md",
        "Corruption Recovery Report",
        "PASS" if rejection_counts else "FAIL",
        [
            "This report is generated from `data/phase6/rejected/rejected_samples.csv`.",
            "",
            *[f"- {stage_name}: {count}" for stage_name, count in sorted(rejection_counts.items())],
            "",
            "No rejection log exists yet." if not rejection_counts else "",
        ],
    )

    _write_report(
        audits_dir / "split_integrity_report.md",
        "Split Integrity Report",
        "PASS" if not split_errors else "FAIL",
        [
            *[f"- {name}: {count}" for name, count in split_stats.items()],
            "",
            *(f"- {err}" for err in split_errors[:50]),
        ],
    )

    status = {
        "timestamp": utc_now(),
        "overall_status": overall_status,
        "stage": stage,
        "processed_sample_count": len(samples),
        "class_counts": {cls: counts.get(cls, 0) for cls in CLASS_NAMES},
        "error_count": len(total_errors),
        "reports": [
            "dataset_audit.md",
            "class_balance_report.md",
            "duplicate_audit.md",
            "preprocessing_consistency_report.md",
            "corruption_recovery_report.md",
            "split_integrity_report.md",
        ],
    }
    (audits_dir / "audit_status.json").write_text(json.dumps(status, indent=2))
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ASTRA Phase 6 dataset")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--stage", type=int, default=0)
    args = parser.parse_args()
    status = run_audit(data_root=args.data_root, stage=args.stage)
    print(json.dumps(status, indent=2))
    if status["overall_status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
