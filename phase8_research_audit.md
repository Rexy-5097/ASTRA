# ASTRA Phase 8 — Research Findings Audit Report

This report documents the primary scientific discoveries, class-wise F1 metrics, calibration temperatures, and subgroup performance gaps.

---

## 1. Classification Performance Metrics

The production **ASTRA Hybrid Transformer** model achieves the following verified metrics:
- **Validation Set Accuracy:** **85.82%**
- **Test Set Accuracy:** **78.17%** (95% Bootstrap Confidence Intervals: `[71.13%, 85.21%]`)
- **Macro F1-Score:** **0.7677** (95% Bootstrap Confidence Intervals: `[0.6944, 0.8320]`)
- **Weighted F1-Score:** **0.7784**

---

## 2. Per-Class Diagnostic Performance

| Star Class | Test Set F1-Score | Typical Mistake Profile |
| :--- | :---: | :--- |
| **RR Lyrae** | **0.9394** | Minimal errors, easily resolved by self-attention |
| **Cepheid** | **0.8108** | Rare misclassification to RR Lyrae (1 case) |
| **Eclipsing Binary** | **0.9091** | High morphology separation |
| **Solar-like** | **0.5238** | Confused with stable/stable noise (3 cases) |
| **Stable** | **0.6552** | Confused with low-amplitude solar-like oscillations |

---

## 3. The BLS Periodicity Bottleneck

A comparison of performance across different period sources reveals the primary bottleneck in variable star ML classification:

- **Catalog-Period Subgroup (N=90):** **90.00% Accuracy** (Macro F1 = 0.5602, ECE = 0.0467)
- **BLS-Period Subgroup (N=52):** **57.69% Accuracy** (Macro F1 = 0.3170, ECE = 0.1465)
- **Subgroup Performance Gap:** **-32.31% Accuracy Collapse**

### Findings
When stellar periods are estimated on-the-fly via Box Least Squares (BLS) rather than resolved from historical databases, period estimation errors trigger phase-folding misalignments. This morphological distortion collapses classification accuracy by over **32%**. Addressing the BLS estimation gap remains the highest-priority future research task.
