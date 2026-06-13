"""
ASTRA — Dataset Split Freezing Script.

Performs group-aware splitting on processed TIC_* directories with a fixed random
seed (42), computes split fingerprinting, and writes the frozen split JSON files.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
SPLITS_DIR = PROJECT_ROOT / "splits"


def main() -> None:
    # 1. Scan for valid TIC directories
    tic_dirs = sorted(DATA_DIR.glob("TIC_*"))
    valid_tic_ids: list[str] = []
    
    required_files = ("flux_1000.npy", "flux_200.npy", "folded_flux_1000.npy", "folded_flux_200.npy", "metadata.json")
    
    for tic_dir in tic_dirs:
        if not tic_dir.is_dir():
            continue
        # Check that all required files exist
        if all((tic_dir / f).exists() for f in required_files):
            valid_tic_ids.append(tic_dir.name)

    print(f"Found {len(valid_tic_ids)} valid stellar directories.")
    
    if len(valid_tic_ids) == 0:
        print("❌ ERROR: No processed stars found in data/processed/. Run batch preprocessing first.")
        return

    # 2. Perform GroupShuffleSplit to split TIC groups
    # Group aware partitioning ensures that all files of the same star stay in the same split.
    # Since each star directory is uniquely identified by its TIC ID, and we have exactly
    # 1 folder per star, each folder is its own group.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    indices = np.arange(len(valid_tic_ids))
    train_idx, val_idx = next(gss.split(indices, groups=valid_tic_ids))

    train_ids = sorted([valid_tic_ids[i] for i in train_idx])
    val_ids = sorted([valid_tic_ids[i] for i in val_idx])

    # 3. Compute unique split fingerprint (SHA256 hash of sorted ID strings)
    hasher = hashlib.sha256()
    hasher.update(json.dumps(train_ids).encode("utf-8"))
    hasher.update(json.dumps(val_ids).encode("utf-8"))
    split_hash = hasher.hexdigest()

    # 4. Prepare metadata
    split_metadata = {
        "seed": 42,
        "dataset_size": len(valid_tic_ids),
        "grouping_key": "tic_id",
        "preprocess_version": "phase4_corrected_pipeline",
        "train_size": len(train_ids),
        "val_size": len(val_ids),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "split_hash": split_hash,
    }

    # 5. Write outputs
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(SPLITS_DIR / "train_ids.json", "w") as f:
        json.dump(train_ids, f, indent=2)
    with open(SPLITS_DIR / "val_ids.json", "w") as f:
        json.dump(val_ids, f, indent=2)
    with open(SPLITS_DIR / "split_metadata.json", "w") as f:
        json.dump(split_metadata, f, indent=2)

    print(f"\n✅ Frozen splits created successfully in {SPLITS_DIR}:")
    print(f"  Train size: {len(train_ids)} stars")
    print(f"  Val size:   {len(val_ids)} stars")
    print(f"  Split hash: {split_hash}")


if __name__ == "__main__":
    main()
