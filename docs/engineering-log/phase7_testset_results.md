# ASTRA Phase 7A — Test Set Evaluation Results

This report documents the exact metrics achieved by all 5 retrained architectures on the held-out test split (N=142) of the 944-star frozen dataset.

## 1. Summary of Test Set Performance

| Architecture | Test Accuracy | 95% CI (Accuracy) | Macro F1 | 95% CI (Macro F1) | Weighted F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 78.17% | `[71.13%, 84.51%]` | 0.7654 | `[0.6840, 0.8317]` | 0.7738 |
| **SHARED** | 78.17% | `[71.13%, 85.21%]` | 0.7677 | `[0.6944, 0.8320]` | 0.7784 |
| **CROSS** | 80.99% | `[73.94%, 87.32%]` | 0.7949 | `[0.7252, 0.8594]` | 0.8033 |
| **SEPARATE** | 84.51% | `[78.17%, 90.16%]` | 0.8394 | `[0.7712, 0.9012]` | 0.8456 |
| **ONLY** | 72.54% | `[64.79%, 80.28%]` | 0.7127 | `[0.6420, 0.7834]` | 0.7247 |

## 2. Per-Class F1-scores on Test Set

| Architecture | RR Lyrae | Cepheid | Eclipsing Binary | Solar-like | Stable |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 0.9538 | 0.8000 | 0.8235 | 0.6341 | 0.6154 |
| **SHARED** | 0.9394 | 0.8108 | 0.9091 | 0.5238 | 0.6552 |
| **CROSS** | 0.9394 | 0.8219 | 0.8750 | 0.6286 | 0.7097 |
| **SEPARATE** | 0.9538 | 0.8857 | 0.9091 | 0.7273 | 0.7213 |
| **ONLY** | 0.9062 | 0.7500 | 0.8889 | 0.4186 | 0.6000 |

## 3. Subgroup Performance (Catalog vs BLS)

| Architecture | Catalog Accuracy (N=90) | BLS Accuracy (N=52) | Catalog Macro F1 | BLS Macro F1 |
| :--- | :---: | :---: | :---: | :---: |
| **CNN_DUAL** | 91.11% | 55.77% | 0.5640 | 0.2667 |
| **SHARED** | 90.00% | 57.69% | 0.5602 | 0.3170 |
| **CROSS** | 91.11% | 63.46% | 0.7016 | 0.2801 |
| **SEPARATE** | 91.11% | 73.08% | 0.7065 | 0.3055 |
| **ONLY** | 84.44% | 51.92% | 0.5374 | 0.2258 |

## 4. Verification Paths Used

- Test Split: `data/phase6/splits/test_ids.json` (SHA256: `2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0`)
- Datasets: `data/phase6/processed/`
- Checkpoints:
  - `cnn_dual`: `models/saved/best_star_cnn_dual_aug.pt`
  - `shared`: `models/saved/best_star_transformer_shared.pt`
  - `cross`: `models/saved/best_star_transformer_cross.pt`
  - `separate`: `models/saved/best_star_transformer_separate.pt`
  - `only`: `models/saved/best_star_transformer_only.pt`
- Confusion Matrices:
  - `cnn_dual`: `models/saved/test_confusion_matrix_cnn_dual.png`
  - `shared`: `models/saved/test_confusion_matrix_shared.png`
  - `cross`: `models/saved/test_confusion_matrix_cross.png`
  - `separate`: `models/saved/test_confusion_matrix_separate.png`
  - `only`: `models/saved/test_confusion_matrix_only.png`
