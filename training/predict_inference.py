"""
ASTRA — PyTorch MC Dropout Inference Engine.

Loads the best PyTorch checkpoint, performs 30 Monte Carlo Dropout passes
on CPU to compute class probabilities, predictive entropy, and run variance.
Outputs findings in JSON format.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES
from training.models.hybrid_transformer import HybridTransformer

CALIBRATION_TEMP = 1.257665  # Phase 7C optimized temperature scaling value

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

def enable_dropout(model: nn.Module) -> None:
    """Keep dropout layers active during evaluation mode."""
    model.eval()
    for m in model.modules():
        if isinstance(m, nn.Dropout):
            m.train()

def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA PyTorch MC Dropout Inference")
    parser.add_argument("--input", type=str, required=True, help="Path to stellar directory containing flux_1000.npy")
    parser.add_argument("--checkpoint", type=str, default="models/saved/best_star_transformer_shared.pt", help="Path to model checkpoint")
    args = parser.parse_args()

    input_dir = Path(args.input)
    checkpoint_path = PROJECT_ROOT / args.checkpoint

    if not input_dir.exists():
        print(json.dumps({"error": f"Input directory {input_dir} not found."}))
        sys.exit(1)

    if not checkpoint_path.exists():
        print(json.dumps({"error": f"Checkpoint {checkpoint_path} not found."}))
        sys.exit(1)

    flux_path = input_dir / "flux_1000.npy"
    meta_path = input_dir / "metadata.json"

    if not flux_path.exists() or not meta_path.exists():
        print(json.dumps({"error": f"Missing raw files in {input_dir}."}))
        sys.exit(1)

    # Load input data
    flux_1000 = np.load(flux_path).astype(np.float32)
    with open(meta_path, "r") as f:
        metadata = json.load(f)

    folded_path = input_dir / "folded_flux_1000.npy"
    if folded_path.exists():
        folded_flux = np.load(folded_path).astype(np.float32)
    else:
        period = metadata.get("period", 1.0)
        n_clean = metadata.get("n_points_clean", 1000)
        cadence = metadata.get("source_cadence", 30.0)
        folded_flux = fold_light_curve_linear(flux_1000, period, n_clean, cadence)

    # Set CPU execution to be fully robust under child execution threads
    device = torch.device("cpu")

    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model = HybridTransformer(variant=ckpt["variant"], num_classes=ckpt["num_classes"])
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)

    # Enable MC Dropout
    enable_dropout(model)

    # Prepare batch tensor: shape (1, 2, 1000)
    inp = torch.tensor(np.stack([flux_1000, folded_flux], axis=0), dtype=torch.float32).unsqueeze(0).to(device)

    num_passes = 30
    all_pass_probs = []
    with torch.no_grad():
        for _ in range(num_passes):
            logits = model(inp)
            calibrated_logits = logits / CALIBRATION_TEMP
            probs = F.softmax(calibrated_logits, dim=-1)
            all_pass_probs.append(probs.cpu().numpy()[0])

    pass_probs = np.stack(all_pass_probs, axis=0) # shape (30, 5)
    mean_probs = np.mean(pass_probs, axis=0) # shape (5,)

    predicted_label = int(np.argmax(mean_probs))
    calibrated_confidence = float(mean_probs[predicted_label])
    entropy = compute_entropy(mean_probs)
    variance = float(np.var(pass_probs[:, predicted_label]))

    output_report = {
        "tic_id": metadata.get("tic_id"),
        "true_class": metadata.get("astra_class"),
        "predicted_class": CLASS_NAMES[predicted_label],
        "calibrated_confidence": calibrated_confidence,
        "entropy": entropy,
        "variance": variance,
        "probabilities": {name: float(mean_probs[i]) for i, name in enumerate(CLASS_NAMES)}
    }

    print(json.dumps(output_report))

if __name__ == "__main__":
    main()
