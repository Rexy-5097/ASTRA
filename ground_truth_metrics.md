# ASTRA Phase 7C — Ground Truth Metrics Report

This report documents the verification of validation and test split metrics, F1-scores with bootstrap CIs, and mistake profiles.

## 1. Validation Accuracy Verification

- **CNN Dual Branch Validation Accuracy**: `85.11%` (Reported: `85.11%` | Mismatch: **None**)
- **Transformer Shared Validation Accuracy**: `85.82%` (Reported: `85.82%` | Mismatch: **None**)

## 2. Test Set Performance Recomputation (with 95% Bootstrap CIs)

| Architecture | Test Accuracy | 95% CI (Accuracy) | Macro F1 | 95% CI (Macro F1) | Weighted F1 | 95% CI (Weighted F1) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CNN DUAL** | 78.17% | `[71.83%, 84.51%]` | 0.7635 | `[0.6923, 0.8301]` | 0.7756 | `[0.7052, 0.8435]` |
| **TRANSFORMER SHARED** | 78.17% | `[71.13%, 85.21%]` | 0.7677 | `[0.6944, 0.8320]` | 0.7784 | `[0.7076, 0.8485]` |

## 3. Recomputed Per-Class F1-scores

| Architecture | RR Lyrae | Cepheid | Eclipsing Binary | Solar-like | Stable |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CNN DUAL** | 0.9394 | 0.7838 | 0.8696 | 0.5128 | 0.7119 |
| **TRANSFORMER SHARED** | 0.9394 | 0.8108 | 0.9091 | 0.5238 | 0.6552 |

## 4. Confusion Matrix Mistake Profiling

Evaluating specific critical scientific classification failure modes:

| Failure Mode (Mistake) | CNN Dual Branch Counts | Transformer Shared Counts |
| :--- | :---: | :---: |
| **RR Lyrae $\rightarrow$ Cepheid** | 0 | 0 |
| **Cepheid $\rightarrow$ RR Lyrae** | 1 | 0 |
| **Eclipsing Binary $\rightarrow$ Cepheid** | 1 | 0 |
| **Solar-like $\rightarrow$ Stable** | 3 | 5 |
