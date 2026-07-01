# ASTRA Phase 7B — Test Set Evaluation Results (Round 1)

This report documents the exact raw performance metrics achieved by the retrained CNN Dual Branch and Transformer Shared architectures on the scientifically frozen test split (N=142).

## 1. Summary of Test Set Performance (Raw Models)

| Architecture | Test Accuracy | 95% CI (Accuracy) | Macro F1 | 95% CI (Macro F1) | Weighted F1 | 95% CI (Weighted F1) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 78.17% | `[71.83%, 84.51%]` | 0.7635 | `[0.6923, 0.8301]` | 0.7756 | `[0.7052, 0.8435]` |
| **TRANSFORMER_SHARED** | 78.17% | `[71.13%, 85.21%]` | 0.7677 | `[0.6944, 0.8320]` | 0.7784 | `[0.7076, 0.8485]` |

## 2. Per-Class F1-scores on Test Set

| Architecture | RR Lyrae | Cepheid | Eclipsing Binary | Solar-like | Stable |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 0.9394 | 0.7838 | 0.8696 | 0.5128 | 0.7119 |
| **TRANSFORMER_SHARED** | 0.9394 | 0.8108 | 0.9091 | 0.5238 | 0.6552 |

## 3. Key Conclusion

**Question:** Does the Shared Transformer still outperform the CNN when trained on a scientifically frozen 944-star benchmark?

**Answer:** **NO.** The Transformer Shared achieved a test set accuracy of `78.17%` (95% CI: `[71.13%, 85.21%]`), compared to `78.17%` (95% CI: `[71.83%, 84.51%]`) for the CNN Dual Branch model.

## 4. Verification Details

- Test Split: `data/phase6/splits/test_ids.json`
- Checkpoints:
  - `cnn_dual`: `models/saved/best_star_cnn_dual_aug.pt`
  - `transformer_shared`: `models/saved/best_star_transformer_shared.pt`
- Confusion Matrices:
  - `cnn_dual`: [test_confusion_matrix_cnn_dual.png](file:////Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3/test_confusion_matrix_cnn_dual.png)
  - `transformer_shared`: [test_confusion_matrix_transformer_shared.png](file:////Users/soumyadebtripathy/.gemini/antigravity/brain/7aa41dc5-db47-45ef-8656-9ec7563f47c3/test_confusion_matrix_transformer_shared.png)
