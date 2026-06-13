"""
ASTRA — Post-Training Temperature Scaling Calibration Script.

Loads the best trained shared transformer model, extracts validation logits,
optimizes a temperature scaling parameter T using L-BFGS to minimize validation NLL,
computes ECE (with adaptive binning), Brier Score, and NLL before/after,
and saves diagnostic plots and calibration_report.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from training.dataset import ASTRADataset
from training.models.hybrid_transformer import HybridTransformer

# Output paths
ARTIFACT_DIR = Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3")
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "saved" / "best_star_transformer_shared.pt"


def compute_calibration_metrics(probs: torch.Tensor, labels: torch.Tensor, n_bins: int = 5) -> tuple[float, float, float, list[dict]]:
    """Compute NLL, Brier Score, and Expected Calibration Error (ECE) using adaptive (equal-frequency) bins."""
    n_samples = len(labels)
    
    # 1. Negative Log Likelihood (NLL)
    # Clamp probs to prevent log(0)
    eps = 1e-15
    probs_clamped = torch.clamp(probs, min=eps, max=1.0 - eps)
    nll = F.nll_loss(torch.log(probs_clamped), labels).item()
    
    # 2. Brier Score
    num_classes = probs.size(-1)
    targets_onehot = F.one_hot(labels, num_classes=num_classes).float()
    brier_score = torch.mean(torch.sum((probs - targets_onehot) ** 2, dim=-1)).item()
    
    # 3. Expected Calibration Error (ECE) with Adaptive (equal-frequency) binning
    confidences, predictions = torch.max(probs, dim=1)
    accuracies = predictions.eq(labels)
    
    # Sort by confidence
    sorted_indices = torch.argsort(confidences)
    sorted_confidences = confidences[sorted_indices]
    sorted_accuracies = accuracies[sorted_indices].float()
    
    bin_size = n_samples // n_bins
    ece = 0.0
    bins_info = []
    
    for i in range(n_bins):
        start_idx = i * bin_size
        end_idx = (i + 1) * bin_size if i < n_bins - 1 else n_samples
        
        bin_confidences = sorted_confidences[start_idx:end_idx]
        bin_accuracies = sorted_accuracies[start_idx:end_idx]
        
        bin_weight = len(bin_confidences) / n_samples
        bin_acc = bin_accuracies.mean().item()
        bin_conf = bin_confidences.mean().item()
        
        ece += bin_weight * abs(bin_acc - bin_conf)
        bins_info.append({
            "bin_idx": i,
            "acc": bin_acc,
            "conf": bin_conf,
            "min_conf": bin_confidences[0].item(),
            "max_conf": bin_confidences[-1].item(),
            "size": len(bin_confidences)
        })
        
    return ece, nll, brier_score, bins_info


def plot_reliability_diagram(bins_info: list[dict], ece: float, title: str, save_path: Path) -> None:
    """Plot reliability diagram with adaptive bin bounds."""
    confs = [b["conf"] for b in bins_info]
    accs = [b["acc"] for b in bins_info]
    bin_edges = [bins_info[0]["min_conf"]] + [b["max_conf"] for b in bins_info]
    
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Perfect calibration line
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration")
    
    # Plot bars
    x_positions = np.arange(len(confs))
    ax.bar(x_positions, accs, width=0.4, alpha=0.7, color="royalblue", edgecolor="black", label="Accuracy")
    ax.bar(x_positions + 0.4, confs, width=0.4, alpha=0.7, color="salmon", edgecolor="black", label="Confidence")
    
    # Set labels
    ax.set_xticks(x_positions + 0.2)
    labels = [f"Bin {i}\n[{b['min_conf']:.2f}-{b['max_conf']:.2f}]" for i, b in enumerate(bins_info)]
    ax.set_xticklabels(labels, fontsize=8)
    
    ax.set_xlabel("Confidence Bin Interval", fontsize=12)
    ax.set_ylabel("Rate", fontsize=12)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"{title}\n(ECE: {ece:.4f})", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_confidence_histograms(confidences_before: np.ndarray, confidences_after: np.ndarray, save_path: Path) -> None:
    """Plot confidence distributions before and after calibration."""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    ax.hist(confidences_before, bins=10, range=(0, 1), alpha=0.5, color="red", label="Before Calibration", edgecolor="black")
    ax.hist(confidences_after, bins=10, range=(0, 1), alpha=0.5, color="green", label="After Calibration", edgecolor="black")
    
    ax.set_xlabel("Predicted Confidence (Max Prob)", fontsize=12)
    ax.set_ylabel("Stellar Counts", fontsize=12)
    ax.set_title("Stellar Confidence Distributions", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def main() -> None:
    print("=" * 70)
    print("  ASTRA Temperature Scaling Calibration")
    print("=" * 70)
    
    if not CHECKPOINT_PATH.exists():
        print(f"❌ ERROR: Checkpoint not found at {CHECKPOINT_PATH}. Run training first.")
        sys.exit(1)
        
    device = torch.device("cpu")  # cpu is fine for calibration
    
    # ── 1. Load Validation Data ──
    val_dataset = ASTRADataset(data_dir=PROJECT_ROOT / "data" / "phase6" / "processed", split="val", use_folded=True)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # ── 2. Load Checkpoint ──
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    model = HybridTransformer(variant=ckpt["variant"], num_classes=ckpt["num_classes"])
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    # ── 3. Extract Logits and Labels ──
    all_logits = []
    all_labels = []
    
    with torch.no_grad():
        for flux, label in val_loader:
            logits = model(flux)
            all_logits.append(logits)
            all_labels.append(label)
            
    logits = torch.cat(all_logits, dim=0)
    labels = torch.cat(all_labels, dim=0)
    
    # ── 4. Compute Metrics BEFORE Calibration ──
    probs_before = F.softmax(logits, dim=-1)
    ece_before, nll_before, brier_before, bins_before = compute_calibration_metrics(probs_before, labels, n_bins=5)
    
    print("\nMetrics BEFORE Temperature Scaling:")
    print(f"  Expected Calibration Error (ECE): {ece_before:.4f}")
    print(f"  Negative Log Likelihood (NLL):     {nll_before:.4f}")
    print(f"  Brier Score:                       {brier_before:.4f}")
    
    # ── 5. Optimize Temperature T using L-BFGS ──
    # We define temperature as a parameter log_T to ensure T = exp(log_T) > 0
    log_temperature = nn.Parameter(torch.zeros(1))
    optimizer = optim.LBFGS([log_temperature], lr=0.01, max_iter=500)
    
    def eval_loss():
        optimizer.zero_grad()
        temp = torch.exp(log_temperature)
        loss = F.cross_entropy(logits / temp, labels)
        loss.backward()
        return loss
        
    optimizer.step(eval_loss)
    
    optimal_T = torch.exp(log_temperature).item()
    print(f"\nOptimal Temperature T: {optimal_T:.4f}")
    with open(PROJECT_ROOT / "models" / "saved" / "optimal_temperature.txt", "w") as f:
        f.write(f"{optimal_T:.6f}\n")
    
    # ── 6. Compute Metrics AFTER Calibration ──
    calibrated_logits = logits / optimal_T
    probs_after = F.softmax(calibrated_logits, dim=-1)
    ece_after, nll_after, brier_after, bins_after = compute_calibration_metrics(probs_after, labels, n_bins=5)
    
    print("\nMetrics AFTER Temperature Scaling:")
    print(f"  Expected Calibration Error (ECE): {ece_after:.4f}")
    print(f"  Negative Log Likelihood (NLL):     {nll_after:.4f}")
    print(f"  Brier Score:                       {brier_after:.4f}")
    
    # ── 7. Generate Diagrams and Plots ──
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    
    plot_reliability_diagram(bins_before, ece_before, "Reliability Diagram (Before Scaling)", ARTIFACT_DIR / "reliability_before.png")
    plot_reliability_diagram(bins_after, ece_after, "Reliability Diagram (After Scaling)", ARTIFACT_DIR / "reliability_after.png")
    
    confidences_before = probs_before.max(dim=1).values.numpy()
    confidences_after = probs_after.max(dim=1).values.numpy()
    plot_confidence_histograms(confidences_before, confidences_after, ARTIFACT_DIR / "confidence_histograms.png")
    
    print(f"\nReliability diagram plots saved to {ARTIFACT_DIR}")
    
    # ── 8. Generate calibration_report.md ──
    report_lines = [
        "# ASTRA — Post-Training Calibration and Calibration Report",
        "",
        "This report documents the post-training calibration (Temperature Scaling) of the production-frozen ASTRA variable star classifier model.",
        "",
        "> [!WARNING]",
        "> **Calibration Limitation Note**:",
        "> Due to the current limited variable star sample size (269 stars total), calibration parameter optimization and verification was performed directly on the model-selection validation split (N=54). Future development should introduce a dedicated held-out calibration split when dataset scale increases.",
        "",
        "## 1. Optimal Temperature Parameter",
        "",
        f"- **Optimal Temperature ($T$)**: `{optimal_T:.4f}`",
        "",
        "A temperature $T < 1$ compresses the logits, indicating the model was slightly underconfident, whereas $T > 1$ dilates logits, smoothing confidence predictions.",
        "",
        "## 2. Calibration Metrics Summary",
        "",
        "| Metric | Before Calibration | After Calibration | Performance Delta |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Expected Calibration Error (ECE)** | {ece_before:.4f} | {ece_after:.4f} | **{ece_after - ece_before:+.4f}** (lower is better) |",
        f"| **Negative Log Likelihood (NLL)** | {nll_before:.4f} | {nll_after:.4f} | **{nll_after - nll_before:+.4f}** (lower is better) |",
        f"| **Brier Score** | {brier_before:.4f} | {brier_after:.4f} | **{brier_after - brier_before:+.4f}** (lower is better) |",
        "",
        "## 3. Reliability Bins Details (Adaptive Binning)",
        "",
        "Because of the sparse validation counts (54 samples), we use adaptive (equal-frequency) bins where each bin contains an equal slice of predicted confidences. This prevents ECE score variance inflation.",
        "",
        "### Bins Details (Before Scaling)",
        "",
        "| Bin Index | Confidence Range | Mean Confidence | Actual Accuracy | Bin Size |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ]
    for b in bins_before:
        report_lines.append(f"| {b['bin_idx']} | [{b['min_conf']:.4f} - {b['max_conf']:.4f}] | {b['conf']:.4f} | {b['acc']:.4f} | {b['size']} |")
        
    report_lines.extend([
        "",
        "### Bins Details (After Scaling)",
        "",
        "| Bin Index | Confidence Range | Mean Confidence | Actual Accuracy | Bin Size |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ])
    for b in bins_after:
        report_lines.append(f"| {b['bin_idx']} | [{b['min_conf']:.4f} - {b['max_conf']:.4f}] | {b['conf']:.4f} | {b['acc']:.4f} | {b['size']} |")
        
    report_lines.extend([
        "",
        "## 4. Visual Diagnostics Reference",
        "",
        "The following diagnostic plots are stored in the artifact workspace:",
        "- **Reliability Diagrams (Before/After)**: [reliability_before.png](file:///Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3/reliability_before.png) and [reliability_after.png](file:///Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3/reliability_after.png)",
        "- **Confidence Histograms**: [confidence_histograms.png](file:///Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3/confidence_histograms.png)",
    ])
    
    report_path = ARTIFACT_DIR / "calibration_report.md"
    report_path.write_text("\n".join(report_lines) + "\n")
    print(f"Calibration report written successfully → {report_path}")


if __name__ == "__main__":
    main()
