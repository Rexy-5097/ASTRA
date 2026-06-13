"""
ASTRA — Upload Pipeline Preprocessing and Explainable Inference Engine.

Takes raw flux values and a folding period, normalizes and resamples the light curve
to match the training distribution, folds the light curve, runs ONNX explainable
inference, and outputs a complete scientific JSON report.
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

CALIBRATION_TEMP = 1.257665
CLASS_NAMES = ["rr_lyrae", "cepheid", "eclipsing_binary", "solar_like", "stable"]

def preprocess_raw_flux(raw_flux: list[float]) -> np.ndarray:
    """Clean, clip outliers, normalize median, and resample to exactly 1000 points."""
    flux = np.array(raw_flux, dtype=np.float32)
    # Remove NaNs and Infs
    flux = flux[np.isfinite(flux)]
    if len(flux) < 50:
        raise ValueError(f"Insufficient valid observations: found {len(flux)}, minimum 50 required.")
        
    # 3-sigma outlier clipping
    mean, std = np.mean(flux), np.std(flux)
    if std > 0:
        flux = np.clip(flux, mean - 3 * std, mean + 3 * std)
        
    # Median detrending
    med = np.median(flux)
    if abs(med) > 1e-5:
        flux = (flux - med) / abs(med)
    else:
        flux = flux - med
        
    # Resample to exactly 1000 points
    x_orig = np.linspace(0, 1, len(flux))
    x_new = np.linspace(0, 1, 1000)
    flux_1000 = np.interp(x_new, x_orig, flux).astype(np.float32)
    
    # Z-score normalization
    std_1000 = flux_1000.std()
    if std_1000 > 0:
        flux_1000 = (flux_1000 - flux_1000.mean()) / std_1000
    else:
        flux_1000 = flux_1000 - flux_1000.mean()
        
    return flux_1000

def fold_light_curve_linear(flux_1000: np.ndarray, period: float) -> np.ndarray:
    """Fold 1000-point normalized flux at period and binned phase fold."""
    # Assuming standard cadence of 30 mins, 1000 points represents ~20.8 days
    T_tot = 1000 * (30.0 / 1440.0)
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
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def compute_entropy(probs: np.ndarray) -> float:
    eps = 1e-15
    probs_clamped = np.clip(probs, eps, 1.0)
    return float(-np.sum(probs * np.log(probs_clamped)))

def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Custom Upload Inference Engine")
    parser.add_argument("--flux", type=str, required=True, help="Comma-separated raw flux values or path to raw flux file")
    parser.add_argument("--period", type=float, required=True, help="Stellar period to fold at (in days)")
    parser.add_argument("--tic_id", type=str, default="999999999", help="Optional target identification")
    parser.add_argument("--onnx", type=str, default="models/saved/best_star_transformer_shared_explain.onnx", help="Path to explainable ONNX model")
    args = parser.parse_args()
    
    onnx_path = PROJECT_ROOT / args.onnx
    
    if not onnx_path.exists():
        print(json.dumps({"error": f"ONNX checkpoint {onnx_path} not found."}))
        sys.exit(1)
        
    # Parse flux input
    try:
        if "," in args.flux:
            raw_flux = [float(x) for x in args.flux.split(",") if x.strip()]
        elif Path(args.flux).exists():
            with open(args.flux, "r") as f:
                content = f.read().replace("\n", ",").replace(" ", ",")
                raw_flux = [float(x) for x in content.split(",") if x.strip()]
        else:
            raw_flux = [float(x) for x in args.flux.split(" ") if x.strip()]

    except Exception as e:
        print(json.dumps({"error": f"Failed to parse flux input: {str(e)}"}))
        sys.exit(1)
        
    # Preprocess
    try:
        flux_1000 = preprocess_raw_flux(raw_flux)
    except Exception as e:
        print(json.dumps({"error": f"Preprocessing failed: {str(e)}"}))
        sys.exit(1)
        
    # Fold
    folded_flux = fold_light_curve_linear(flux_1000, args.period)
    
    # Prepare batch tensor: shape (1, 2, 1000)
    input_tensor = np.stack([flux_1000, folded_flux], axis=0)[np.newaxis, ...]
    
    # Run ONNX session
    sess = ort.InferenceSession(str(onnx_path))
    input_name = sess.get_inputs()[0].name
    
    outputs = sess.run(
        ["logits", "attention_weights", "cnn_features", "pooled_features"],
        {input_name: input_tensor}
    )
    
    logits, attn_w, cnn_feats, pooled_feats = outputs
    
    # Calibration
    calibrated_logits = logits[0] / CALIBRATION_TEMP
    probabilities = softmax(calibrated_logits)
    predicted_class_idx = int(np.argmax(probabilities))
    predicted_class = CLASS_NAMES[predicted_class_idx]
    
    entropy = compute_entropy(probabilities)
    
    # Prepare outputs
    attention_matrix = attn_w[0].tolist()
    cnn_sequence_importance = np.mean(np.abs(cnn_feats[0]), axis=0).tolist()
    
    # Sample down original and folded light curve to 200 points for lighter client charts
    # slice step = 5 for 1000 points
    sampled_raw = flux_1000[::5].tolist()
    sampled_folded = folded_flux[::5].tolist()
    
    output_report = {
        "tic_id": args.tic_id,
        "predicted_class": predicted_class,
        "calibrated_confidence": float(probabilities[predicted_class_idx]),
        "entropy": entropy,
        "probabilities": {name: float(probabilities[i]) for i, name in enumerate(CLASS_NAMES)},
        "attention_weights": attention_matrix,
        "cnn_features_importance": cnn_sequence_importance,
        "pooled_features": pooled_feats[0].tolist(),
        "period": args.period,
        "period_source": "custom_upload",
        "flux_200": sampled_raw,
        "folded_flux_200": sampled_folded
    }
    
    print(json.dumps(output_report))

if __name__ == "__main__":
    main()
