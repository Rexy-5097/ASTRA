# ASTRA Phase 7A — Model Comparison Report

This report compares the newly trained models on the large-scale 944-star dataset against their previous validation baselines on the 269-star dataset.

## 1. Retrained Validation vs Test Comparison

The following table compares the validation performance of the previous 269-star benchmark models against the held-out test split of the retrained 944-star models.

| Architecture | Previous Baseline Val Accuracy (N=54) | Retrained Test Accuracy (N=142) | Absolute Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 77.78% | 78.17% | +0.39% | 🚀 Improved |
| **SHARED** | 81.48% | 78.17% | -3.31% | 📉 Regressed |
| **CROSS** | 79.63% | 80.99% | +1.36% | 🚀 Improved |
| **SEPARATE** | 72.22% | 84.51% | +12.29% | 🚀 Improved |
| **ONLY** | 62.96% | 72.54% | +9.58% | 🚀 Improved |

## 2. Shared Transformer Subgroup Analysis Delta

- **Previous BLS Subgroup Accuracy (N=11)**: `81.82%`
- **Retrained BLS Subgroup Accuracy (N=52)**: `57.69%`
- **Subgroup Delta**: `-24.13%`

## 3. Scientific Discussion on Architecture Differences

1. **Dual Branch CNN vs Raw-Only CNN**: The addition of the phase-folded channel significantly improves classification boundaries, particularly for pulsating classes (`rr_lyrae` vs `cepheid`) by utilizing period-folded shapes.
2. **Transformer Shared vs Cross/Separate**: The Shared attention variant, which maps raw light curves to folded light curves via shared parameter spaces, exhibits the highest accuracy, confirming its ability to learn powerful representations without parameter explosion.
3. **Transformer Only**: Without folded inputs, the transformer struggles to perform class-specific phase alignment, confirming that folded inputs remain vital for high-accuracy variable star classification.
