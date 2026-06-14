"""
ASTRA — CommandLine Production Inference Script.

Loads a stellar observation directory (flux_1000.npy and metadata.json),
computes phase-folded representation if missing, runs inference,
and prints predicted class, probabilities, entropy, and uncertainty scores.

Usage:
    python training/predict.py --input data/processed/TIC_109718459/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES, LABEL_TO_NAME
from training.models.hybrid_transformer import HybridTransformer

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

CALIBRATION_TEMP = 1.2944  # Pre-optimized temperature scaling value


def fold_light_curve_linear(flux_1000: np.ndarray, period: float, n_points_clean: int, source_cadence: float) -> np.ndarray:
    """Fold flux array using linear approximation of time when FITS files are not available."""
    T_tot = n_points_clean * (source_cadence / 1440.0)
    time_arr = np.linspace(0, T_tot, 1000)
    phase = ((time_arr - time_arr[0]) % period) / period
    sort_idx = np.argsort(phase)
    phase_sorted = phase[sort_idx]
    flux_sorted = flux_1000[sort_idx]

    FLUX_1000_LEN = 1000
    bin_edges = np.linspace(0, 1, FLUX_1000_LEN + 1)
    folded = np.zeros(FLUX_1000_LEN, dtype=np.float32)
    for i in range(FLUX_1000_LEN):
        mask = ((phase_sorted >= bin_edges[i]) & (phase_sorted < bin_edges[i+1]))
        if np.any(mask):
            folded[i] = np.mean(flux_sorted[mask])
        else:
            folded[i] = np.interp((bin_edges[i] + bin_edges[i+1])/2, phase_sorted, flux_sorted)

    std = folded.std()
    if std > 0:
        folded = (folded - folded.mean()) / std
    return folded


def compute_entropy(probs: np.ndarray) -> float:
    """Compute Shannon entropy."""
    eps = 1e-15
    probs_clamped = np.clip(probs, eps, 1.0)
    return float(-np.sum(probs * np.log(probs_clamped)))


def save_attention_map(attention_weights: torch.Tensor, output_path: Path) -> None:
    """Generate and save 2D heatmap of model attention weights."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # attention_weights shape: (n_heads, L, L) or (L, L)
    if attention_weights.ndim == 3:
        # Average across attention heads
        weights = torch.mean(attention_weights, dim=0).numpy()
    else:
        weights = attention_weights.numpy()

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(weights, cmap="viridis", ax=ax)
    ax.set_xlabel("Keys (Raw + Folded Sequence Token Index)", fontsize=10)
    ax.set_ylabel("Queries (Raw + Folded Sequence Token Index)", fontsize=10)
    ax.set_title("Self-Attention Weights Heatmap", fontsize=11, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    print(f"Attention visualization saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Production Inference CLI")
    parser.add_argument("--input", type=str, required=True, help="Path to stellar directory (e.g. data/processed/TIC_109718459/)")
    parser.add_argument("--checkpoint", type=str, default="models/saved/best_star_transformer_shared.pt", help="Path to best PyTorch model checkpoint")
    parser.add_argument("--attention", action="store_true", help="Save self-attention weights plot in input directory")
    args = parser.parse_args()

    input_dir = Path(args.input)
    checkpoint_path = PROJECT_ROOT / args.checkpoint

    # 1. Validate Input Directory
    if not input_dir.exists():
        print(f"❌ ERROR: Input directory {input_dir} does not exist.")
        sys.exit(1)

    flux_path = input_dir / "flux_1000.npy"
    meta_path = input_dir / "metadata.json"

    if not flux_path.exists():
        print(f"❌ ERROR: Missing flux_1000.npy in {input_dir}.")
        sys.exit(1)
    if not meta_path.exists():
        print(f"❌ ERROR: Missing metadata.json in {input_dir}.")
        sys.exit(1)

    # Load input data
    flux_1000 = np.load(flux_path).astype(np.float32)
    with open(meta_path, "r") as f:
        metadata = json.load(f)

    # Check for folded flux on disk, otherwise fold on-the-fly
    folded_path = input_dir / "folded_flux_1000.npy"
    if folded_path.exists():
        folded_flux = np.load(folded_path).astype(np.float32)
    else:
        print("folded_flux_1000.npy not found on disk. Performing on-the-fly folding...")
        period = metadata.get("period")
        n_clean = metadata.get("n_points_clean")
        cadence = metadata.get("source_cadence", 30.0)

        if period is not None and period > 0 and n_clean is not None:
            folded_flux = fold_light_curve_linear(flux_1000, period, n_clean, cadence)
        else:
            print("  ⚠️ Warning: Missing period in metadata. Using raw flux as folded placeholder.")
            folded_flux = flux_1000.copy()

    # 2. Setup Device & Load Model
    device = torch.device("cpu")
    if torch.backends.mps.is_available():
        device = torch.device("mps")

    if not checkpoint_path.exists():
        print(f"❌ ERROR: Checkpoint not found at {checkpoint_path}.")
        sys.exit(1)

    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model = HybridTransformer(variant=ckpt["variant"], num_classes=ckpt["num_classes"])
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    # Prepare input tensor: shape (1, 2, 1000)
    inp = torch.tensor(np.stack([flux_1000, folded_flux], axis=0), dtype=torch.float32).unsqueeze(0).to(device)

    # 3. Calibrated Inference Pass
    with torch.no_grad():
        logits = model(inp)
        # Apply Temperature Scaling
        calibrated_logits = logits / CALIBRATION_TEMP
        probs = F.softmax(calibrated_logits, dim=-1).cpu().numpy()[0]

    predicted_label = int(np.argmax(probs))
    calibrated_confidence = probs[predicted_label]
    entropy = compute_entropy(probs)

    # 4. Output Results to Stdout
    print("\n" + "=" * 50)
    print("  ASTRA Stellar Inference Classification Results")
    print("=" * 50)
    print(f"Target Directory:    {input_dir.resolve()}")
    print(f"TIC ID:              {metadata.get('tic_id', 'unknown')}")
    print(f"Reference Class:     {metadata.get('astra_class', 'unknown')}")
    print("-" * 50)
    print(f"Predicted Class:     {LABEL_TO_NAME[predicted_label].upper()}")
    print(f"Calibrated Conf:     {calibrated_confidence * 100:.2f}%")
    print(f"Predictive Entropy:  {entropy:.4f} nats")
    print("Calibrated Probabilities:")
    for idx_c, class_name in enumerate(CLASS_NAMES):
        indicator = "★ " if idx_c == predicted_label else "  "
        print(f"  {indicator}{class_name:20s}: {probs[idx_c] * 100:6.2f}%")
    print("=" * 50 + "\n")

    # 5. Optional Attention Map Saving
    if args.attention:
        if getattr(model, "last_attention_weights", None) is not None:
            output_plot = input_dir / "attention_map.png"
            save_attention_map(model.last_attention_weights[0], output_plot)
        else:
            print("⚠️ Attention weights not recorded by model during forward pass.")


if __name__ == "__main__":
    main()
