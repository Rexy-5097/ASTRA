# ASTRA Phase 7B — Temperature Calibration & Test Set Benchmark

This report evaluates temperature calibration parameters optimized on the validation set, and benchmarks calibrated vs raw model outputs on the test set.

## 1. Optimal Temperature Parameters

- **CNN Dual Branch ($T$ optimal)**: `1.0107`
- **Transformer Shared ($T$ optimal)**: `1.2577`

## 2. Calibration Metrics Summary (Before vs. After)

| Architecture | ECE (Before) | ECE (After) | NLL (Before) | NLL (After) | Brier (Before) | Brier (After) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 0.0907 | 0.0907 | 0.5005 | 0.5005 | 0.2620 | 0.2617 |
| **TRANSFORMER_SHARED** | 0.0810 | 0.0442 | 0.6225 | 0.5945 | 0.3146 | 0.3025 |

## 3. MC Dropout Selective Prediction Sweeps

Evaluating accuracy vs coverage as confidence threshold increases (30 stochastic passes):

| Architecture | Threshold | Coverage | Accuracy |
| :--- | :---: | :---: | :---: |
| **CNN_DUAL** | 0.5 | 91.5% | 81.5% |
| **CNN_DUAL** | 0.6 | 81.7% | 87.9% |
| **CNN_DUAL** | 0.7 | 71.1% | 97.0% |
| **CNN_DUAL** | 0.8 | 62.0% | 98.9% |
| **CNN_DUAL** | 0.9 | 48.6% | 100.0% |
| **TRANSFORMER_SHARED** | 0.5 | 87.3% | 84.7% |
| **TRANSFORMER_SHARED** | 0.6 | 81.7% | 87.9% |
| **TRANSFORMER_SHARED** | 0.7 | 72.5% | 92.2% |
| **TRANSFORMER_SHARED** | 0.8 | 62.7% | 93.3% |
| **TRANSFORMER_SHARED** | 0.9 | 43.0% | 98.4% |
