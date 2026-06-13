#!/usr/bin/env python3
"""Freeze leakage-safe ASTRA Phase 6 splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES
from pipeline.phase6_utils import DEFAULT_PHASE6_ROOT, ensure_phase6_structure


def _load_valid_samples(data_root: Path) -> list[dict[str, Any]]:
    samples = []
    for meta_path in sorted((data_root / "processed").glob("TIC_*/metadata.json")):
        try:
            metadata = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("selected_period") is None:
            continue
        samples.append({
            "id": meta_path.parent.name,
            "class": metadata.get("astra_class"),
            "group": metadata.get("duplicate_group_id") or meta_path.parent.name,
        })
    return samples


def _assert_audit_passed(data_root: Path, minimum_samples: int) -> None:
    status_path = data_root / "audits" / "audit_status.json"
    if not status_path.exists():
        raise RuntimeError(f"Missing audit status: {status_path}")
    status = json.loads(status_path.read_text())
    if status.get("overall_status") != "PASS":
        raise RuntimeError("Cannot freeze Phase 6 splits because the latest audit did not pass.")
    if int(status.get("processed_sample_count", 0)) < minimum_samples:
        raise RuntimeError(
            f"Cannot freeze Phase 6 splits before {minimum_samples} samples. "
            f"Found {status.get('processed_sample_count', 0)}."
        )


def freeze_splits(
    data_root: Path = DEFAULT_PHASE6_ROOT,
    seed: int = 42,
    minimum_samples: int = 5000,
    allow_unpassed_audit: bool = False,
) -> dict[str, Any]:
    data_root = ensure_phase6_structure(data_root)
    if not allow_unpassed_audit:
        _assert_audit_passed(data_root, minimum_samples)

    samples = _load_valid_samples(data_root)
    groups: dict[str, dict[str, Any]] = {}
    for sample in samples:
        group = sample["group"]
        if group not in groups:
            groups[group] = {"ids": [], "class": sample["class"]}
        groups[group]["ids"].append(sample["id"])

    by_class: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for group, payload in groups.items():
        by_class[payload["class"]].append((group, payload))

    rng = random.Random(seed)
    split_ids = {"train": [], "val": [], "calibration": [], "test": []}
    ratios = {"train": 0.70, "val": 0.10, "calibration": 0.10, "test": 0.10}

    for cls in CLASS_NAMES:
        cls_groups = by_class.get(cls, [])
        rng.shuffle(cls_groups)
        n = len(cls_groups)
        n_train = int(round(n * ratios["train"]))
        n_val = int(round(n * ratios["val"]))
        n_cal = int(round(n * ratios["calibration"]))
        assignments = (
            [("train", item) for item in cls_groups[:n_train]]
            + [("val", item) for item in cls_groups[n_train:n_train + n_val]]
            + [("calibration", item) for item in cls_groups[n_train + n_val:n_train + n_val + n_cal]]
            + [("test", item) for item in cls_groups[n_train + n_val + n_cal:]]
        )
        for split, (_, payload) in assignments:
            split_ids[split].extend(payload["ids"])

    for split in split_ids:
        split_ids[split] = sorted(split_ids[split])

    hasher = hashlib.sha256()
    for split in ("train", "val", "calibration", "test"):
        hasher.update(json.dumps(split_ids[split]).encode("utf-8"))
    split_hash = hasher.hexdigest()

    split_dir = data_root / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    for split, ids in split_ids.items():
        (split_dir / f"{split}_ids.json").write_text(json.dumps(ids, indent=2))

    metadata = {
        "seed": seed,
        "dataset_size": len(samples),
        "grouping_key": "duplicate_group_id",
        "ratios": ratios,
        "train_size": len(split_ids["train"]),
        "val_size": len(split_ids["val"]),
        "calibration_size": len(split_ids["calibration"]),
        "test_size": len(split_ids["test"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "split_hash": split_hash,
        "minimum_samples_required": minimum_samples,
        "audit_override_used": allow_unpassed_audit,
    }
    (split_dir / "split_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze ASTRA Phase 6 dataset splits")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minimum-samples", type=int, default=5000)
    parser.add_argument("--allow-unpassed-audit", action="store_true")
    args = parser.parse_args()

    metadata = freeze_splits(
        data_root=args.data_root,
        seed=args.seed,
        minimum_samples=args.minimum_samples,
        allow_unpassed_audit=args.allow_unpassed_audit,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
