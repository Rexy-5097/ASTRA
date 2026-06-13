# ASTRA Phase 7C — Ground Truth Split Audit Report

This report documents the verification of dataset splits and class balance parameters.

## 1. Split Size Summary

| Split | Count | Ratio |
| :--- | :---: | :---: |
| Train | 661 | 70.02% |
| Validation | 141 | 14.94% |
| Test | 142 | 15.04% |

## 2. Set Intersection Leakage Checks

- **Overlap Train $\cap$ Validation**: `0`
- **Overlap Train $\cap$ Test**: `0`
- **Overlap Validation $\cap$ Test**: `0`

## 3. Split Class Stratification Balance

| Class | Train count | Validation count | Test count |
| :--- | :---: | :---: | :---: |
| `rr_lyrae` | 152 | 33 | 32 |
| `cepheid` | 161 | 34 | 35 |
| `eclipsing_binary` | 105 | 22 | 23 |
| `solar_like` | 99 | 21 | 22 |
| `stable` | 144 | 31 | 30 |

## 4. Period Source Balance (Catalog vs. BLS)

| Period Source | Train count | Validation count | Test count |
| :--- | :---: | :---: | :---: |
| `catalog` | 418 | 89 | 90 |
| `BLS` | 243 | 52 | 52 |
