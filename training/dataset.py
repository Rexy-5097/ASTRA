"""
ASTRA — PyTorch Dataset for preprocessed stellar light curves.

Loads flux_1000.npy arrays from TIC_* subdirectories under data/processed/,
validates metadata labels, and provides group-aware train/val splitting
(by TIC ID) to prevent data leakage.

Supports optional dual-channel loading (use_folded=True) which stacks
raw flux and phase-folded flux into a (2, 1000) tensor.

Supports optional stochastic data augmentations (augment=True):
  - Gaussian noise
  - Amplitude scaling
  - Temporal shift (raw channel only when folded)
  - Random masking

Provides class_counts and class_weights properties for loss balancing.
"""

import json
import logging
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from sklearn.model_selection import GroupShuffleSplit
from torch.utils.data import Dataset

from data.labels import CLASS_NAMES, LABEL_TO_NAME, NUM_CLASSES

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


TEST_SET_ACCESSED = False


class ASTRADataset(Dataset):
    """PyTorch Dataset for ASTRA stellar light curve classification.

    Each sample is a preprocessed 1000-point flux time series stored as
    ``flux_1000.npy`` inside a ``TIC_*`` subdirectory, paired with an
    integer label from ``metadata.json``.

    Splitting is group-aware: all observations for a given TIC ID stay in
    the same split, preventing data leakage.

    Args:
        data_dir:      Path to the processed data directory (e.g. data/processed/).
        split:         'train' or 'val'.
        val_fraction:  Fraction of groups held out for validation.
        random_seed:   Random seed for reproducible splits.
        use_folded:    If True, also load folded_flux_1000.npy and return
            a (2, 1000) tensor.  Default False returns (1, 1000).
        augment:       If True, apply stochastic augmentations to flux data.
        augment_prob:  Per-augmentation probability (each applied independently).
    """

    REQUIRED_FILES_BASE = ("flux_1000.npy", "flux_200.npy", "metadata.json")
    REQUIRED_FILES_FOLDED = ("folded_flux_1000.npy", "folded_flux_200.npy")

    def __init__(
        self,
        data_dir: Path | str,
        split: str = "train",
        val_fraction: float = 0.2,
        random_seed: int = 42,
        use_folded: bool = False,
        augment: bool = False,
        augment_prob: float = 0.5,
    ) -> None:
        super().__init__()
        self.data_dir = Path(data_dir)
        self.split = split.lower()
        self.use_folded = use_folded
        self.augment = augment
        self.augment_prob = augment_prob
        assert self.split in ("train", "val", "calibration", "test"), (
            f"split must be train, val, calibration, or test; got '{split}'"
        )

        if self.split == "test":
            global TEST_SET_ACCESSED
            TEST_SET_ACCESSED = True


        # Build required-files tuple dynamically based on mode
        self.REQUIRED_FILES: tuple[str, ...] = self.REQUIRED_FILES_BASE
        if self.use_folded:
            self.REQUIRED_FILES = self.REQUIRED_FILES_BASE + self.REQUIRED_FILES_FOLDED

        # ── Scan TIC_* directories ──────────────────────────────────
        all_samples: list[dict[str, Any]] = []
        all_groups: list[str] = []  # TIC IDs for group-aware splitting

        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")

        tic_dirs = sorted(self.data_dir.glob("TIC_*"))
        if not tic_dirs:
            logger.warning(f"No TIC_* directories found in {self.data_dir}")

        for tic_dir in tic_dirs:
            if not tic_dir.is_dir():
                continue

            # Check all required files are present
            missing = [f for f in self.REQUIRED_FILES if not (tic_dir / f).exists()]
            if missing:
                logger.warning(
                    f"Skipping {tic_dir.name}: missing {', '.join(missing)}"
                )
                continue

            # Load and validate metadata
            try:
                with open(tic_dir / "metadata.json", "r") as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Skipping {tic_dir.name}: cannot read metadata.json ({e})")
                continue

            label = metadata.get("label")
            astra_class = metadata.get("astra_class", "unknown")

            if label is None or not isinstance(label, int) or not (0 <= label < NUM_CLASSES):
                logger.warning(
                    f"Skipping {tic_dir.name}: invalid label {label!r} "
                    f"(expected int in 0..{NUM_CLASSES - 1})"
                )
                continue

            # Extract TIC ID for grouping
            tic_id = tic_dir.name  # e.g. "TIC_12345678"

            sample_entry: dict[str, Any] = {
                "flux_path": tic_dir / "flux_1000.npy",
                "label": label,
                "astra_class": astra_class,
                "tic_id": tic_id,
            }
            if self.use_folded:
                sample_entry["folded_flux_path"] = tic_dir / "folded_flux_1000.npy"

            all_samples.append(sample_entry)
            all_groups.append(tic_id)

        # ── Group-aware train/val split ─────────────────────────────
        self._samples: list[dict[str, Any]] = []
        self._label_list: list[int] = []

        if len(all_samples) == 0:
            logger.warning("No valid samples found — dataset is empty.")
            return

        # Check for frozen splits
        if self.data_dir.name == "processed" and self.data_dir.parent.name == "phase6":
            split_dir = self.data_dir.parent / "splits"
        else:
            split_dir = PROJECT_ROOT / "splits"
        split_file = split_dir / f"{self.split}_ids.json"
        metadata_file = split_dir / "split_metadata.json"

        if split_file.exists() and metadata_file.exists():
            with open(split_file, "r") as f:
                frozen_ids = set(json.load(f))
            with open(metadata_file, "r") as f:
                meta = json.load(f)

            expected_size = meta[f"{self.split}_size"]

            # Select samples strictly matching frozen IDs
            for s in all_samples:
                if s["tic_id"] in frozen_ids:
                    self._samples.append(s)
                    self._label_list.append(s["label"])

            # Additional validation
            # 1. Check exact size match
            if len(self._samples) != expected_size:
                raise ValueError(
                    f"Sample count mismatch for split '{self.split}': "
                    f"Expected {expected_size} stars, but got {len(self._samples)}."
                )

            # 2. Check no leakage if both files exist (verify validation set doesn't overlap)
            other_split = "val" if self.split == "train" else "train"
            other_file = split_dir / f"{other_split}_ids.json"
            if other_file.exists():
                with open(other_file, "r") as f:
                    other_ids = set(json.load(f))
                overlap = frozen_ids.intersection(other_ids)
                if overlap:
                    raise ValueError(
                        f"Leakage detected! Overlap between train and val splits: {overlap}"
                    )

            # 3. Check all labels present
            unique_labels = set(self._label_list)
            if len(unique_labels) != NUM_CLASSES:
                raise ValueError(
                    f"Label representation failure in split '{self.split}': "
                    f"Expected {NUM_CLASSES} classes, but found only {len(unique_labels)}."
                )

            logger.info(
                f"ASTRADataset [{self.split}]: Loaded {len(self._samples)} frozen samples "
                f"from {split_file.name} (validated split hash: {meta['split_hash'][:8]})"
            )
        else:
            if self.split in ("calibration", "test"):
                raise ValueError(
                    f"Frozen Phase 6 split file required for split '{self.split}'."
                )
            logger.info("Frozen split not found. Falling back to dynamic GroupShuffleSplit.")
            gss = GroupShuffleSplit(
                n_splits=1, test_size=val_fraction, random_state=random_seed
            )
            groups_array = np.array(all_groups)
            indices = np.arange(len(all_samples))

            train_idx, val_idx = next(gss.split(indices, groups=groups_array))
            selected_idx = train_idx if self.split == "train" else val_idx

            for i in selected_idx:
                self._samples.append(all_samples[i])
                self._label_list.append(all_samples[i]["label"])

        num_tic_groups = len(set(s["tic_id"] for s in self._samples))
        logger.info(
            f"ASTRADataset [{self.split}]: {len(self._samples)} samples "
            f"from {num_tic_groups} TIC groups"
        )

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        """Return (flux_tensor, label) for the given index.

        flux_tensor: shape (1, 1000) or (2, 1000) if use_folded=True
        label:       integer, dtype long
        """
        sample = self._samples[idx]

        # Load raw flux array
        flux = np.load(sample["flux_path"]).astype(np.float32)

        if self.use_folded:
            folded_flux = np.load(sample["folded_flux_path"]).astype(np.float32)
            # Stack: channel 0 = raw, channel 1 = folded → (2, 1000)
            flux_tensor = torch.from_numpy(
                np.stack([flux, folded_flux], axis=0)
            )  # (2, 1000)
        else:
            flux_tensor = torch.from_numpy(flux).unsqueeze(0)  # (1, 1000)

        # Apply augmentations if enabled
        if self.augment:
            flux_tensor = self._apply_augmentations(flux_tensor)

        label = torch.tensor(sample["label"], dtype=torch.long)
        return flux_tensor, label

    # ── Data Augmentations ──────────────────────────────────────────

    def _apply_augmentations(self, flux_tensor: torch.Tensor) -> torch.Tensor:
        """Apply stochastic augmentations to the flux tensor.

        Each augmentation is applied independently with probability
        ``self.augment_prob``.

        When ``use_folded=True`` (2-channel input), augmentations are applied
        consistently to BOTH channels, EXCEPT temporal shift which is only
        applied to the raw channel (channel 0) to preserve phase structure
        in the folded channel.

        Args:
            flux_tensor: shape (C, 1000) where C=1 or C=2

        Returns:
            Augmented tensor of the same shape.
        """
        # 1. Gaussian Noise: add N(0, sigma), sigma ~ U(0.01, 0.05)
        if random.random() < self.augment_prob:
            sigma = random.uniform(0.01, 0.05)
            noise = torch.randn_like(flux_tensor) * sigma
            flux_tensor = flux_tensor + noise

        # 2. Amplitude Scaling: multiply by scale ~ U(0.9, 1.1)
        if random.random() < self.augment_prob:
            scale = random.uniform(0.9, 1.1)
            flux_tensor = flux_tensor * scale

        # 3. Temporal Shift: roll along dim=-1 by random amount in [-50, 50]
        #    Only applied to the raw channel (channel 0), NOT folded channel
        if random.random() < self.augment_prob:
            shift = random.randint(-50, 50)
            if self.use_folded:
                # Roll only the raw channel (channel 0)
                flux_tensor[0] = torch.roll(flux_tensor[0], shifts=shift, dims=-1)
            else:
                flux_tensor = torch.roll(flux_tensor, shifts=shift, dims=-1)

        # 4. Random Masking: zero out a contiguous segment of length U(10, 80)
        if random.random() < self.augment_prob:
            mask_len = random.randint(10, 80)
            seq_len = flux_tensor.shape[-1]
            start = random.randint(0, seq_len - mask_len)
            # Apply to ALL channels for consistency
            flux_tensor[..., start : start + mask_len] = 0.0

        return flux_tensor

    # ── Properties for class balancing ──────────────────────────────

    @property
    def class_counts(self) -> dict[str, int]:
        """Count of samples per class name in this split."""
        counter = Counter(self._label_list)
        return {
            LABEL_TO_NAME[label]: counter.get(label, 0)
            for label in range(NUM_CLASSES)
        }

    @property
    def class_weights(self) -> torch.Tensor:
        """Inverse-frequency weights for loss balancing, shape (NUM_CLASSES,).

        Weight for class c = total_samples / (num_classes * count_c).
        Classes with zero samples receive weight 0.0.
        """
        counter = Counter(self._label_list)
        total = len(self._label_list)
        weights = []
        for c in range(NUM_CLASSES):
            count = counter.get(c, 0)
            if count > 0:
                weights.append(total / (NUM_CLASSES * count))
            else:
                weights.append(0.0)
        return torch.tensor(weights, dtype=torch.float32)


if __name__ == "__main__":
    print("=" * 60)
    print("ASTRADataset — Statistics")
    print("=" * 60)

    data_path = PROJECT_ROOT / "data" / "processed"
    print(f"\nData directory: {data_path}")
    print(f"Exists: {data_path.exists()}")

    if not data_path.exists():
        print("\n⚠ Data directory not found. Run the preprocessing pipeline first.")
        sys.exit(0)

    for split in ("train", "val"):
        print(f"\n{'─' * 40}")
        print(f"Split: {split}")
        print(f"{'─' * 40}")

        ds = ASTRADataset(data_dir=data_path, split=split)
        print(f"  Samples: {len(ds)}")

        if len(ds) == 0:
            print("  (empty)")
            continue

        counts = ds.class_counts
        weights = ds.class_weights
        print("\n  Class distribution:")
        for i, name in enumerate(CLASS_NAMES):
            print(f"    {name:20s}: {counts[name]:5d}  (weight: {weights[i]:.4f})")

        # Test loading a sample
        flux, label = ds[0]
        print("\n  Sample [0]:")
        print(f"    Flux shape: {tuple(flux.shape)}")
        print(f"    Flux dtype: {flux.dtype}")
        print(f"    Label:      {label.item()} ({LABEL_TO_NAME[label.item()]})")

    # ── Test augmentation pipeline (unit test with synthetic data) ──
    print(f"\n{'─' * 40}")
    print("Augmentation Smoke Test (synthetic)")
    print(f"{'─' * 40}")

    # Single-channel augmentations
    dummy = torch.ones(1, 1000)
    ds_aug = ASTRADataset.__new__(ASTRADataset)
    ds_aug.use_folded = False
    ds_aug.augment = True
    ds_aug.augment_prob = 1.0  # force all augmentations
    augmented = ds_aug._apply_augmentations(dummy.clone())
    print(f"  Single-channel: input shape {tuple(dummy.shape)} → output shape {tuple(augmented.shape)}")
    assert augmented.shape == (1, 1000), f"Shape mismatch: {augmented.shape}"

    # Dual-channel augmentations
    dummy2 = torch.ones(2, 1000)
    ds_aug.use_folded = True
    augmented2 = ds_aug._apply_augmentations(dummy2.clone())
    print(f"  Dual-channel:   input shape {tuple(dummy2.shape)} → output shape {tuple(augmented2.shape)}")
    assert augmented2.shape == (2, 1000), f"Shape mismatch: {augmented2.shape}"

    print("\n✅ Dataset verification complete!")
