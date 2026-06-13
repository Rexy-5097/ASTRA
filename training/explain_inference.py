"""
ASTRA — Explainable ONNX Inference Engine.

Loads the explainable ONNX checkpoint, processes a target's photometric arrays,
runs inference using ONNX Runtime, applies temperature scaling, and outputs
a detailed scientific explainability report in JSON format.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Scientific Constants
CALIBRATION_TEMP = 1.257665  # Phase 7C optimized temperature scaling value
CLASS_NAMES = ["rr_lyrae", "cepheid", "eclipsing_binary", "solar_like", "stable"]

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

def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def compute_entropy(probs: np.ndarray) -> float:
    """Compute Shannon entropy in nats."""
    eps = 1e-15
    probs_clamped = np.clip(probs, eps, 1.0)
    return float(-np.sum(probs * np.log(probs_clamped)))

def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Explainable Inference Engine")
    parser.add_argument("--input", type=str, required=True, help="Path to stellar directory containing flux_1000.npy and metadata.json")
    parser.add_argument("--onnx", type=str, default="models/saved/best_star_transformer_shared_explain.onnx", help="Path to explainable ONNX model")
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    onnx_path = PROJECT_ROOT / args.onnx
    
    if not input_dir.exists():
        print(json.dumps({"error": f"Input directory {input_dir} not found."}))
        sys.exit(1)
        
    if not onnx_path.exists():
        print(json.dumps({"error": f"ONNX model checkpoint {onnx_path} not found."}))
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
        
    # Fold lightcurve on-the-fly or read from disk
    folded_path = input_dir / "folded_flux_1000.npy"
    if folded_path.exists():
        folded_flux = np.load(folded_path).astype(np.float32)
    else:
        period = metadata.get("period", 1.0)
        n_clean = metadata.get("n_points_clean", 1000)
        cadence = metadata.get("source_cadence", 30.0)
        folded_flux = fold_light_curve_linear(flux_1000, period, n_clean, cadence)
        
    # Prepare input batch: shape (1, 2, 1000)
    input_tensor = np.stack([flux_1000, folded_flux], axis=0)[np.newaxis, ...]
    
    # Initialize ONNX session
    sess = ort.InferenceSession(str(onnx_path))
    input_name = sess.get_inputs()[0].name
    
    # Run session returning multiple explainability channels
    outputs = sess.run(
        ["logits", "attention_weights", "cnn_features", "pooled_features"],
        {input_name: input_tensor}
    )
    
    logits, attn_w, cnn_feats, pooled_feats = outputs
    
    # Apply temperature calibration scaling
    calibrated_logits = logits[0] / CALIBRATION_TEMP
    probabilities = softmax(calibrated_logits)
    predicted_class_idx = int(np.argmax(probabilities))
    predicted_class = CLASS_NAMES[predicted_class_idx]
    
    entropy = compute_entropy(probabilities)
    
    # Compute attention weights averaged across heads if needed (already shape [B, 250, 250])
    # attn_w shape is [1, 250, 250]
    attention_matrix = attn_w[0].tolist()
    
    # Compute average CNN feature activations along sequence length (to plot feature importance)
    # cnn_feats shape is [1, 128, 250] -> average over 128 channels -> shape 250
    cnn_sequence_importance = np.mean(np.abs(cnn_feats[0]), axis=0).tolist()
    
    # Format and output JSON
    output_report = {
        "tic_id": metadata.get("tic_id"),
        "true_class": metadata.get("astra_class"),
        "predicted_class": predicted_class,
        "calibrated_confidence": float(probabilities[predicted_class_idx]),
        "entropy": entropy,
        "probabilities": {name: float(probabilities[i]) for i, name in enumerate(CLASS_NAMES)},
        "attention_weights": attention_matrix,
        "cnn_features_importance": cnn_sequence_importance,
        "pooled_features": pooled_feats[0].tolist(),
        "period": metadata.get("period"),
        "period_source": metadata.get("period_source")
    }
    
    print(json.dumps(output_report))

if __name__ == "__main__":
    main()
