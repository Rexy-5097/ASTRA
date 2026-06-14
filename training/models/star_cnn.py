"""
ASTRA — StarCNN: 1D Convolutional Neural Network for stellar light curve classification.

Architecture: 5 convolutional blocks with batch normalization and pooling,
followed by a 3-layer fully connected classifier head with dropout.

Supports an optional dual-branch mode (use_folded=True) that processes
raw flux and phase-folded flux through independent CNN branches before
concatenation and classification.

Input (default):      (batch, 1, 1000) — single-channel flux time series
Input (use_folded):   (batch, 2, 1000) — ch0=raw flux, ch1=folded flux
Output:               (batch, num_classes) — class logits

Target parameter count: ~1.14M (default), ~1.5–1.75M (dual-branch)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn

from data.labels import NUM_CLASSES


class StarCNN(nn.Module):
    """1D CNN for stellar light curve classification.

    Args:
        num_classes: Number of output classes.
        use_folded:  If True, expect (batch, 2, 1000) input and use
                     dual-branch architecture (raw + folded).  Default
                     False preserves the original single-branch model.

    Architecture (default — single branch):
        5 conv blocks (1→32→64→128→256→512) + 3-layer classifier head
        Target parameter count: ~1.14M

    Architecture (dual branch):
        raw_branch:    5 blocks identical to default (→ 512-dim)
        folded_branch: 4 lighter blocks 1→32→64→128→256 (→ 256-dim)
        Concatenated 768-dim → 3-layer dual_classifier head
        Target parameter count: ~1.5–1.75M
    """

    def __init__(
        self,
        num_classes: int = NUM_CLASSES,
        use_folded: bool = False,
    ) -> None:
        super().__init__()
        self.use_folded = use_folded

        if self.use_folded:
            # ── Dual-branch mode ────────────────────────────────────

            # Raw branch: independent 5-block CNN (same architecture as
            # single-branch), 1→32→64→128→256→512 with AdaptiveAvgPool → 512-dim
            self.raw_branch = nn.Sequential(
                # Block 1: 1 → 32, kernel=7
                nn.Conv1d(1, 32, kernel_size=7, padding=3),
                nn.BatchNorm1d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (32, 500)
                # Block 2: 32 → 64, kernel=5
                nn.Conv1d(32, 64, kernel_size=5, padding=2),
                nn.BatchNorm1d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (64, 250)
                # Block 3: 64 → 128, kernel=5
                nn.Conv1d(64, 128, kernel_size=5, padding=2),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (128, 125)
                # Block 4: 128 → 256, kernel=3
                nn.Conv1d(128, 256, kernel_size=3, padding=1),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (256, 62)
                # Block 5: 256 → 512, kernel=3, global pool
                nn.Conv1d(256, 512, kernel_size=3, padding=1),
                nn.BatchNorm1d(512),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool1d(1),  # (512, 1)
            )

            # Folded branch: lighter 4-block CNN
            # 1→32→64→128→256, kernel sizes 7,5,5,3 with AdaptiveAvgPool → 256-dim
            self.folded_branch = nn.Sequential(
                # Folded block 1: 1 → 32, kernel=7
                nn.Conv1d(1, 32, kernel_size=7, padding=3),
                nn.BatchNorm1d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (32, 500)
                # Folded block 2: 32 → 64, kernel=5
                nn.Conv1d(32, 64, kernel_size=5, padding=2),
                nn.BatchNorm1d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (64, 250)
                # Folded block 3: 64 → 128, kernel=5
                nn.Conv1d(64, 128, kernel_size=5, padding=2),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (128, 125)
                # Folded block 4: 128 → 256, kernel=3
                nn.Conv1d(128, 256, kernel_size=3, padding=1),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),  # (256, 62)
                # Global pool → 256-dim
                nn.AdaptiveAvgPool1d(1),  # (256, 1)
            )

            # Dual classifier head: 768 → 384 → 128 → num_classes
            self.dual_classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(768, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(inplace=True),
                nn.Dropout(0.4),
                nn.Linear(384, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3),
                nn.Linear(128, num_classes),
            )
        else:
            # ── Single-branch mode (original architecture) ──────────

            # Block 1: 1 → 32, kernel=7
            self.block1 = nn.Sequential(
                nn.Conv1d(1, 32, kernel_size=7, padding=3),
                nn.BatchNorm1d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )  # output: (32, 500)

            # Block 2: 32 → 64, kernel=5
            self.block2 = nn.Sequential(
                nn.Conv1d(32, 64, kernel_size=5, padding=2),
                nn.BatchNorm1d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )  # output: (64, 250)

            # Block 3: 64 → 128, kernel=5
            self.block3 = nn.Sequential(
                nn.Conv1d(64, 128, kernel_size=5, padding=2),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )  # output: (128, 125)

            # Block 4: 128 → 256, kernel=3
            self.block4 = nn.Sequential(
                nn.Conv1d(128, 256, kernel_size=3, padding=1),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )  # output: (256, 62)

            # Block 5: 256 → 512, kernel=3, global pool
            self.block5 = nn.Sequential(
                nn.Conv1d(256, 512, kernel_size=3, padding=1),
                nn.BatchNorm1d(512),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool1d(1),
            )  # output: (512, 1)

            # Original classifier head
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(512, 768),
                nn.BatchNorm1d(768),
                nn.ReLU(inplace=True),
                nn.Dropout(0.5),
                nn.Linear(768, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3),
                nn.Linear(256, num_classes),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_folded:
            raw = x[:, 0:1, :]       # (B, 1, 1000)
            folded = x[:, 1:2, :]    # (B, 1, 1000)

            raw_feat = self.raw_branch(raw)          # (B, 512, 1)
            folded_feat = self.folded_branch(folded)  # (B, 256, 1)

            combined = torch.cat(
                [raw_feat.squeeze(-1), folded_feat.squeeze(-1)], dim=1
            )  # (B, 768)

            return self.dual_classifier(combined)
        else:
            # Original single-branch path
            x = self.block1(x)
            x = self.block2(x)
            x = self.block3(x)
            x = self.block4(x)
            x = self.block5(x)
            x = self.classifier(x)
            return x

    @staticmethod
    def count_parameters(model: nn.Module) -> dict[str, int]:
        """Count total and trainable parameters."""
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return {"total": total, "trainable": trainable}


if __name__ == "__main__":
    # ── Test 1: Original single-branch mode ─────────────────────
    print("=" * 60)
    print("StarCNN — Architecture Verification")
    print("=" * 60)

    model = StarCNN(num_classes=NUM_CLASSES, use_folded=False)
    params = StarCNN.count_parameters(model)

    print("\n[Mode: single-branch (use_folded=False)]")
    print(f"  Num classes:          {NUM_CLASSES}")
    print(f"  Total parameters:     {params['total']:,}")
    print(f"  Trainable parameters: {params['trainable']:,}")

    # Per-block breakdown
    print("\nPer-block parameter counts:")
    for name in ["block1", "block2", "block3", "block4", "block5", "classifier"]:
        block = getattr(model, name)
        block_params = sum(p.numel() for p in block.parameters())
        print(f"  {name:12s}: {block_params:>10,}")

    # Dummy forward pass
    print("\nRunning dummy forward pass...")
    dummy_input = torch.randn(2, 1, 1000)
    with torch.no_grad():
        output = model(dummy_input)
    print(f"  Input shape:  {tuple(dummy_input.shape)}")
    print(f"  Output shape: {tuple(output.shape)}")

    assert output.shape == (2, NUM_CLASSES), (
        f"Expected output shape (2, {NUM_CLASSES}), got {tuple(output.shape)}"
    )
    print("\n✅ Single-branch verification passed!")

    # ── Test 2: Dual-branch mode ────────────────────────────────
    print("\n" + "=" * 60)
    print("StarCNN — Dual-Branch (use_folded=True)")
    print("=" * 60)

    model_dual = StarCNN(num_classes=NUM_CLASSES, use_folded=True)
    params_dual = StarCNN.count_parameters(model_dual)

    print("\n[Mode: dual-branch (use_folded=True)]")
    print(f"  Num classes:          {NUM_CLASSES}")
    print(f"  Total parameters:     {params_dual['total']:,}")
    print(f"  Trainable parameters: {params_dual['trainable']:,}")

    # Per-component breakdown
    print("\nPer-component parameter counts:")
    for name in ["raw_branch", "folded_branch", "dual_classifier"]:
        component = getattr(model_dual, name)
        comp_params = sum(p.numel() for p in component.parameters())
        print(f"  {name:20s}: {comp_params:>10,}")

    # Dummy forward pass with 2-channel input
    print("\nRunning dummy forward pass (2-channel input)...")
    dummy_input_dual = torch.randn(2, 2, 1000)
    with torch.no_grad():
        output_dual = model_dual(dummy_input_dual)
    print(f"  Input shape:  {tuple(dummy_input_dual.shape)}")
    print(f"  Output shape: {tuple(output_dual.shape)}")

    assert output_dual.shape == (2, NUM_CLASSES), (
        f"Expected output shape (2, {NUM_CLASSES}), got {tuple(output_dual.shape)}"
    )

    # Verify parameter count is in expected range
    # raw_branch ~546K + folded_branch ~151K + dual_classifier ~346K ≈ 1.04M
    assert 1_000_000 <= params_dual["total"] <= 1_200_000, (
        f"Expected dual-branch params in 1.0M–1.2M, got {params_dual['total']:,}"
    )
    print(f"\n✅ Dual-branch verification passed! ({params_dual['total']:,} params)")
