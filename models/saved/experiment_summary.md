# ASTRA — Experiment Comparison Report

Generated: 2026-05-26T21:19:45.569664+00:00

## Experiment Overview

| Experiment | Mode | Augment | Best Epoch | Val Accuracy | Params |
|------------|------|---------|------------|--------------|--------|
| raw_aug | Raw-only | ✅ | 10 | 0.7222 (72.22%) | 1,140,101 |
| dual_aug | Dual-branch | ✅ | 12 | 0.7778 (77.78%) | 1,043,333 |

---

## Classification Report — `raw_aug`

```
precision    recall  f1-score   support

        rr_lyrae       0.92      0.85      0.88        13
         cepheid       0.60      1.00      0.75         9
eclipsing_binary       1.00      0.70      0.82        10
      solar_like       0.67      0.22      0.33         9
          stable       0.59      0.77      0.67        13

        accuracy                           0.72        54
       macro avg       0.75      0.71      0.69        54
    weighted avg       0.76      0.72      0.71        54
```

## Classification Report — `dual_aug`

```
precision    recall  f1-score   support

        rr_lyrae       1.00      0.92      0.96        13
         cepheid       0.70      0.78      0.74         9
eclipsing_binary       0.82      0.90      0.86        10
      solar_like       0.75      0.67      0.71         9
          stable       0.62      0.62      0.62        13

        accuracy                           0.78        54
       macro avg       0.78      0.78      0.78        54
    weighted avg       0.78      0.78      0.78        54
```

---

## Analysis

- **raw_aug** accuracy: 0.7222
- **dual_aug** accuracy: 0.7778
- **Delta**: +0.0556 (+5.56%)

> Compare the per-class precision/recall above to assess whether phase-folding reduced Cepheid vs RR Lyrae confusion specifically.

Confusion matrices saved to:
- `confusion_matrix_raw_aug.png`
- `confusion_matrix_dual_aug.png`
