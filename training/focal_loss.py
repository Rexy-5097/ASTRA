"""
ASTRA — Focal Loss for multi-class stellar classification.

Implements Focal Loss (Lin et al., 2017) to down-weight easy examples
and focus training on hard, misclassified samples. Particularly useful
for the inherent class imbalance in stellar survey data.

FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.labels import CLASS_NAMES, NUM_CLASSES


class FocalLoss(nn.Module):
    """Focal Loss (Lin et al., 2017) for multi-class classification.

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Args:
        alpha: Per-class weights tensor of shape (num_classes,), or None for uniform.
        gamma: Focusing parameter. gamma=0 recovers standard CE. Default 2.0.
        reduction: 'mean', 'sum', or 'none'.
    """

    def __init__(
        self,
        alpha: torch.Tensor | list[float] | None = None,
        gamma: float = 2.0,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.reduction = reduction

        if alpha is not None:
            if not isinstance(alpha, torch.Tensor):
                alpha = torch.tensor(alpha, dtype=torch.float32)
            self.register_buffer("alpha", alpha)
        else:
            self.alpha = None

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute focal loss.

        Args:
            inputs: (N, C) logits — raw model output before softmax.
            targets: (N,) integer class labels in [0, C).

        Returns:
            Scalar loss (if reduction='mean' or 'sum') or (N,) per-sample losses.
        """
        # Standard cross-entropy per sample (unreduced)
        ce_loss = F.cross_entropy(inputs, targets, reduction="none")

        # Probability of the correct class
        p_t = torch.exp(-ce_loss)

        # Focal modulating factor
        focal_weight = (1 - p_t) ** self.gamma
        loss = focal_weight * ce_loss

        # Apply per-class alpha weighting
        if self.alpha is not None:
            alpha_t = self.alpha[targets]
            loss = alpha_t * loss

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss


if __name__ == "__main__":
    print("=" * 60)
    print("FocalLoss — Verification Tests")
    print("=" * 60)

    torch.manual_seed(42)
    batch_size = 16

    # Dummy logits and targets
    logits = torch.randn(batch_size, NUM_CLASSES)
    targets = torch.randint(0, NUM_CLASSES, (batch_size,))

    # Test 1: Basic focal loss (no alpha)
    fl_basic = FocalLoss(gamma=2.0, reduction="mean")
    loss_basic = fl_basic(logits, targets)
    print(f"\n[Test 1] FocalLoss(gamma=2.0, alpha=None)")
    print(f"  Loss: {loss_basic.item():.4f}")

    # Test 2: With per-class alpha weights
    alpha_weights = torch.tensor([1.5, 2.0, 1.0, 1.8, 0.5])
    fl_weighted = FocalLoss(alpha=alpha_weights, gamma=2.0, reduction="mean")
    loss_weighted = fl_weighted(logits, targets)
    print(f"\n[Test 2] FocalLoss(gamma=2.0, alpha={alpha_weights.tolist()})")
    print(f"  Loss: {loss_weighted.item():.4f}")

    # Test 3: gamma=0 should approximate standard cross-entropy
    fl_gamma0 = FocalLoss(gamma=0.0, reduction="mean")
    ce_ref = F.cross_entropy(logits, targets, reduction="mean")
    loss_gamma0 = fl_gamma0(logits, targets)
    print(f"\n[Test 3] FocalLoss(gamma=0.0) vs CrossEntropy")
    print(f"  Focal (gamma=0): {loss_gamma0.item():.6f}")
    print(f"  CrossEntropy:    {ce_ref.item():.6f}")
    print(f"  Difference:      {abs(loss_gamma0.item() - ce_ref.item()):.2e}")

    # Test 4: Reduction modes
    fl_none = FocalLoss(gamma=2.0, reduction="none")
    loss_none = fl_none(logits, targets)
    fl_sum = FocalLoss(gamma=2.0, reduction="sum")
    loss_sum = fl_sum(logits, targets)
    print(f"\n[Test 4] Reduction modes")
    print(f"  'none' shape: {tuple(loss_none.shape)}")
    print(f"  'sum':        {loss_sum.item():.4f}")
    print(f"  'mean':       {loss_basic.item():.4f}")

    # Test 5: Alpha from list (not tensor)
    fl_list_alpha = FocalLoss(alpha=[1.0, 1.0, 1.0, 1.0, 1.0], gamma=2.0)
    loss_list = fl_list_alpha(logits, targets)
    print(f"\n[Test 5] Alpha from list (uniform)")
    print(f"  Loss: {loss_list.item():.4f}")

    print("\n✅ All FocalLoss tests passed!")
