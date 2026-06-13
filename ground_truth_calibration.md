# ASTRA Phase 7C — Ground Truth Calibration Report

This report documents recomputed optimal scaling temperatures, global ECE, per-class ECE, NLL, and Brier scores.

## 1. Optimal Scaling Temperatures (Optimized on Validation)

- **CNN Dual Branch ($T_{cnn}$)**: `1.010702`
- **Transformer Shared ($T_{trans}$)**: `1.257665`

## 2. Global Test Split Calibration Summary

| Model | ECE (Raw) | ECE (Calibrated) | NLL (Raw) | NLL (Calibrated) | Brier (Raw) | Brier (Calibrated) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CNN DUAL** | 0.0907 | 0.0907 | 0.0907 | 0.0907 | 0.2620 | 0.2617 |
| **TRANSFORMER SHARED** | 0.0810 | 0.0442 | 0.0810 | 0.0442 | 0.3146 | 0.3025 |

## 3. Class-Specific Calibration Error (ECE before vs. after)

| Class Label | CNN (Raw) | CNN (Calibrated) | Transformer (Raw) | Transformer (Calibrated) |
| :--- | :---: | :---: | :---: | :---: |
| `rr_lyrae` | 0.0255 | 0.0259 | 0.0143 | 0.0252 |
| `cepheid` | 0.0137 | 0.0135 | 0.0158 | 0.0141 |
| `eclipsing_binary` | 0.0089 | 0.0085 | 0.0101 | 0.0155 |
| `solar_like` | 0.0228 | 0.0221 | 0.0908 | 0.0628 |
| `stable` | 0.0354 | 0.0360 | 0.0732 | 0.0685 |
