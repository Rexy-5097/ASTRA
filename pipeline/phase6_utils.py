#!/usr/bin/env python3
"""Shared helpers for the ASTRA Phase 6 data pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PHASE6_ROOT = PROJECT_ROOT / "data" / "phase6"

PHASE6_DIRS = (
    "raw",
    "processed",
    "catalogs",
    "splits",
    "audits",
    "rejected",
    "logs",
)

PHASE6_PREPROCESSING_VERSION = "phase6_preprocess_v1"

PHASE6_REQUIRED_METADATA = (
    "tic_id",
    "source_catalogs",
    "primary_source",
    "ra",
    "dec",
    "cadence_type",
    "sector_information",
    "catalog_period",
    "bls_period",
    "selected_period",
    "period_source",
    "variability_amplitude",
    "snr_estimate",
    "preprocessing_version",
    "preprocessing_hash",
    "raw_file_hashes",
    "processed_file_hashes",
    "processing_timestamp",
)

MANIFEST_COLUMNS = (
    "tic_id",
    "source_catalogs",
    "primary_source",
    "ra",
    "dec",
    "astra_class",
    "catalog_label",
    "catalog_period",
    "crossmatch_status",
    "label_confidence",
    "tess_available",
    "cadence_candidates",
    "sector_candidates",
    "duplicate_group_id",
    "review_duplicate_group_id",
    "rejection_status",
    "name",
    "vsx_type",
    "label_conflict",
)

REJECTED_COLUMNS = (
    "timestamp",
    "tic_id",
    "name",
    "astra_class",
    "stage",
    "reason",
    "source_catalogs",
    "primary_source",
)

PERIOD_REQUIRED_CLASSES = {"rr_lyrae", "cepheid", "eclipsing_binary"}


def ensure_phase6_structure(data_root: Path = DEFAULT_PHASE6_ROOT) -> Path:
    """Create the Phase 6 directory layout and artifact/log directories."""
    data_root = Path(data_root)
    for name in PHASE6_DIRS:
        (data_root / name).mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "models" / "artifacts").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    return data_root


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_tic_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    text = text.upper().replace("TIC", "").replace("_", "").strip()
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def tic_dir_name(tic_id: Any) -> str:
    text = normalize_tic_id(tic_id)
    return f"TIC_{text}" if text else "TIC_UNKNOWN"


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def array_content_hash(arr: np.ndarray) -> str:
    hasher = hashlib.sha256()
    hasher.update(str(arr.dtype).encode("utf-8"))
    hasher.update(json.dumps(arr.shape).encode("utf-8"))
    hasher.update(np.ascontiguousarray(arr).tobytes())
    return hasher.hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="") as fp:
        return list(csv.DictReader(fp))


def write_csv_rows(path: Path, rows: Iterable[dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    field_list = list(fieldnames)
    with open(path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=field_list)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in field_list})


def append_csv_row(path: Path, row: dict[str, Any], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    field_list = list(fieldnames)
    exists = path.exists()
    with open(path, "a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=field_list)
        if not exists:
            writer.writeheader()
        writer.writerow({key: _csv_value(row.get(key, "")) for key in field_list})


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def parse_jsonish_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v)]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(v) for v in parsed if str(v)]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in text.split("|") if part.strip()]


def angular_separation_arcsec(
    ra1: float | None,
    dec1: float | None,
    ra2: float | None,
    dec2: float | None,
) -> float:
    if None in (ra1, dec1, ra2, dec2):
        return math.inf
    r1 = math.radians(float(ra1))
    d1 = math.radians(float(dec1))
    r2 = math.radians(float(ra2))
    d2 = math.radians(float(dec2))
    sin_d = math.sin((d2 - d1) / 2.0)
    sin_r = math.sin((r2 - r1) / 2.0)
    a = sin_d * sin_d + math.cos(d1) * math.cos(d2) * sin_r * sin_r
    return math.degrees(2.0 * math.asin(min(1.0, math.sqrt(a)))) * 3600.0


def assign_duplicate_groups(
    rows: list[dict[str, Any]],
    strict_radius_arcsec: float = 2.0,
    review_radius_arcsec: float = 10.0,
) -> list[dict[str, Any]]:
    """Assign duplicate groups by TIC first, then strict coordinate radius."""
    grouped_rows = [dict(row) for row in rows]
    parent = list(range(len(grouped_rows)))
    review_pairs: list[tuple[int, int]] = []

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    tic_seen: dict[str, int] = {}
    for idx, row in enumerate(grouped_rows):
        tic = normalize_tic_id(row.get("tic_id"))
        if tic:
            if tic in tic_seen:
                union(idx, tic_seen[tic])
            else:
                tic_seen[tic] = idx

    for i, left in enumerate(grouped_rows):
        for j in range(i + 1, len(grouped_rows)):
            right = grouped_rows[j]
            try:
                sep = angular_separation_arcsec(
                    _float_or_none(left.get("ra")),
                    _float_or_none(left.get("dec")),
                    _float_or_none(right.get("ra")),
                    _float_or_none(right.get("dec")),
                )
            except (TypeError, ValueError):
                sep = math.inf
            if sep <= strict_radius_arcsec:
                union(i, j)
            elif sep <= review_radius_arcsec:
                review_pairs.append((i, j))

    root_to_group: dict[int, str] = {}
    for idx, row in enumerate(grouped_rows):
        root = find(idx)
        if root not in root_to_group:
            root_to_group[root] = f"dup_{len(root_to_group) + 1:07d}"
        row["duplicate_group_id"] = root_to_group[root]
        row.setdefault("review_duplicate_group_id", "")

    for review_index, (left, right) in enumerate(review_pairs, start=1):
        group_id = f"review_{review_index:07d}"
        grouped_rows[left]["review_duplicate_group_id"] = group_id
        grouped_rows[right]["review_duplicate_group_id"] = group_id

    return grouped_rows


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def class_counts_from_metadata(processed_root: Path) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for meta_path in sorted(Path(processed_root).glob("TIC_*/metadata.json")):
        try:
            metadata = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        counts[str(metadata.get("astra_class", "unknown"))] += 1
    return dict(counts)


def validate_phase6_metadata(metadata: dict[str, Any]) -> list[str]:
    """Return validation errors for the Phase 6 metadata contract."""
    errors: list[str] = []
    for key in PHASE6_REQUIRED_METADATA:
        if key not in metadata:
            errors.append(f"missing metadata field {key}")
    if metadata.get("selected_period") is None:
        errors.append("selected_period is required")
    if metadata.get("period") != metadata.get("selected_period"):
        errors.append("period alias must equal selected_period")
    if not isinstance(metadata.get("raw_file_hashes"), dict) or not metadata.get("raw_file_hashes"):
        errors.append("raw_file_hashes must be a non-empty dict")
    if not isinstance(metadata.get("processed_file_hashes"), dict) or not metadata.get("processed_file_hashes"):
        errors.append("processed_file_hashes must be a non-empty dict")
    if metadata.get("snr_estimate") is None:
        errors.append("snr_estimate is required")
    if metadata.get("period_source") not in {"catalog", "BLS"}:
        errors.append("period_source must be catalog or BLS")
    return errors


def assert_phase6_training_allowed(data_dir: Path, minimum_samples: int = 900) -> None:
    """Block training on Phase 6 data until the audit and split gates pass."""
    data_dir = Path(data_dir).resolve()
    phase6_root = DEFAULT_PHASE6_ROOT.resolve()
    try:
        is_phase6 = data_dir == phase6_root or phase6_root in data_dir.parents
    except RuntimeError:
        is_phase6 = "phase6" in data_dir.parts

    if not is_phase6:
        return

    status_path = phase6_root / "audits" / "audit_status.json"
    if not status_path.exists():
        raise RuntimeError(
            f"Refusing to train on Phase 6 data. Missing audit status: {status_path}"
        )
    status = json.loads(status_path.read_text())
    if status.get("overall_status") != "PASS":
        raise RuntimeError("Refusing to train on Phase 6 data. The latest dataset audit did not pass.")
    if int(status.get("processed_sample_count", 0)) < minimum_samples:
        raise RuntimeError(
            f"Refusing to train on Phase 6 data before {minimum_samples} verified samples."
        )
    class_count = list(status.get("class_counts", {}).values())
    assert min(class_count) >= 100, f"Class count floor violation: minimum is {min(class_count)}"

    for split in ("train", "val", "calibration", "test"):
        if not (phase6_root / "splits" / f"{split}_ids.json").exists():
            raise RuntimeError(f"Refusing to train on Phase 6 data. Missing {split}_ids.json.")
