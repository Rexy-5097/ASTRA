# ASTRA Phase 7C — Ground Truth Uncertainty Report

This report documents recomputed MC Dropout uncertainty metrics, entropy distributions for correct/incorrect predictions, and error detection capabilities.

## 1. Shannon Entropy Distributions for Correct vs. Incorrect Predictions

| Model | Correct Pred Mean Entropy | Correct Pred Entropy Var | Incorrect Pred Mean Entropy | Incorrect Pred Entropy Var |
| :--- | :---: | :---: | :---: | :---: |
| **CNN DUAL** | 0.4381 | 0.0969 | 0.9769 | 0.0588 |
| **TRANSFORMER SHARED** | 0.4973 | 0.0964 | 0.9998 | 0.1038 |

## 2. Error Detection Performance (AUROC using Predictive Entropy)

- **CNN Dual Branch AUROC**: `0.9015`
- **Transformer Shared AUROC**: `0.8628`

An AUROC closer to 1.0 indicates that high entropy (uncertainty) is strongly correlated with actual classification errors.

## 3. Recomputed Coverage & Accuracy Sweeps

| Model | Confidence Threshold | Recomputed Coverage | Recomputed Accuracy |
| :--- | :---: | :---: | :---: |
| **CNN DUAL** | 0.5 | 91.5% | 82.3% |
| **CNN DUAL** | 0.6 | 83.1% | 87.3% |
| **CNN DUAL** | 0.7 | 73.2% | 94.2% |
| **CNN DUAL** | 0.8 | 62.7% | 97.8% |
| **CNN DUAL** | 0.9 | 47.2% | 100.0% |
| **TRANSFORMER SHARED** | 0.5 | 86.6% | 84.6% |
| **TRANSFORMER SHARED** | 0.6 | 78.9% | 88.4% |
| **TRANSFORMER SHARED** | 0.7 | 71.8% | 92.2% |
| **TRANSFORMER SHARED** | 0.8 | 63.4% | 93.3% |
| **TRANSFORMER SHARED** | 0.9 | 43.0% | 98.4% |
