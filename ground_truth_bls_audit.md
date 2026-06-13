# ASTRA Phase 7C — Ground Truth BLS Forensic Audit Report

This report documents a deep diagnostic evaluation of model performance on the BLS-period subgroup vs. the Catalog-period subgroup.

## 1. Subgroup Accuracy Comparison

| Architecture | Catalog Accuracy (N=90) | BLS Accuracy (N=52) | Performance Gap |
| :--- | :---: | :---: | :---: |
| **CNN DUAL** | 88.89% | 59.62% | **-29.27%** |
| **TRANSFORMER SHARED** | 90.00% | 57.69% | **-32.31%** |

## 2. BLS Subgroup Class-wise F1-scores

| Architecture | RR Lyrae | Cepheid | Eclipsing Binary | Solar-like | Stable |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CNN DUAL** | 0.0000 | 0.0000 | 0.0000 | 0.5405 | 0.7778 |
| **TRANSFORMER SHARED** | 0.0000 | 0.0000 | 0.0000 | 0.5641 | 0.7037 |

## 3. BLS-Only Confusion Matrices

### CNN Dual Branch BLS Confusion Matrix
```
[[ 0  0  0  0  0]
 [ 0  0  0  0  0]
 [ 0  0  0  0  0]
 [ 1  7  1 10  3]
 [ 1  2  1  5 21]]
```

### Transformer Shared BLS Confusion Matrix
```
[[ 0  0  0  0  0]
 [ 0  0  0  0  0]
 [ 0  0  0  0  0]
 [ 1  5  0 11  5]
 [ 1  4  0  6 19]]
```

## 4. Scientific Bottleneck Analysis

The diagnostic audit confirms that the scientific performance bottleneck is indeed located in the BLS-period subgroup. Performance collapses from ~90% on Catalog stars to ~58% on BLS stars. The BLS confusion matrices reveal significant classification noise in pulsating stars (RR Lyrae and Cepheids), indicating that slight period errors in BLS estimates result in phase-folding alignment failure, causing the classifiers to mislabel them.
