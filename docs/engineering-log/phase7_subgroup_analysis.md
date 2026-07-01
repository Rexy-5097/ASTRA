# ASTRA Phase 7B — Subgroup Performance Analysis

This report evaluates performance metrics separately for the Catalog-period and BLS-period subgroups on the test set.

## 1. CNN Dual Branch Subgroup Performance

| Metric | Catalog | BLS |
| :--- | :---: | :---: |
| **Accuracy** | 88.89% | 59.62% |
| **Macro F1** | 0.5540 | 0.2637 |
| **ECE** | 0.0695 | 0.1500 |
| **Coverage @ 0.8 confidence** | 80.0% | 30.8% |

## 2. Transformer Shared Subgroup Performance

| Metric | Catalog | BLS |
| :--- | :---: | :---: |
| **Accuracy** | 90.00% | 57.69% |
| **Macro F1** | 0.5602 | 0.3170 |
| **ECE** | 0.0467 | 0.1465 |
| **Coverage @ 0.8 confidence** | 74.4% | 42.3% |

## 3. Discussion on the BLS Challenge

The BLS-period subgroup represents ASTRA's most interesting scientific challenge, as period estimates are derived dynamically via the Box Least Squares algorithm rather than verified catalogs. Comparing ECE and Coverage @ 0.8 reveals whether the model's self-reported confidence remains well-calibrated when dealing with noisier period estimates.
