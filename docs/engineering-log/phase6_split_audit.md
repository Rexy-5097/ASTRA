# ASTRA Phase 6 Split Audit Report

## 1. Split Sizes
- **Train:** 661 (70.02%)
- **Validation:** 141 (14.94%)
- **Test:** 142 (15.04%)
- **Total:** 944

## 2. Class Balance
| Class | Train | Val | Test | Total | Train % | Val % | Test % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cepheid` | 161 | 34 | 35 | 230 | 24.36% | 24.11% | 24.65% |
| `eclipsing_binary` | 105 | 22 | 23 | 150 | 15.89% | 15.60% | 16.20% |
| `rr_lyrae` | 152 | 33 | 32 | 217 | 23.00% | 23.40% | 22.54% |
| `solar_like` | 99 | 21 | 22 | 142 | 14.98% | 14.89% | 15.49% |
| `stable` | 144 | 31 | 30 | 205 | 21.79% | 21.99% | 21.13% |

## 3. Catalog / BLS Balance
| Source | Train | Val | Test | Total | Train % | Val % | Test % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BLS` | 243 | 52 | 52 | 347 | 36.76% | 36.88% | 36.62% |
| `catalog` | 418 | 89 | 90 | 597 | 63.24% | 63.12% | 63.38% |

## 4. Leakage Verification
- **Direct ID overlap leakage:** 0 (Train/Val: 0, Train/Test: 0, Val/Test: 0)
- **Duplicate TIC leakage:** 0 (all processed TIC IDs are unique)
- **Coordinate leakage (separation <= 10.0 arcsec):** 0

## 5. Class Distribution Drift
Maximum absolute percentage drift from overall dataset proportions for each class:
| Class | Overall % | Train % | Val % | Test % | Max Drift |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cepheid` | 24.36% | 24.36% | 24.11% | 24.65% | 0.28% |
| `eclipsing_binary` | 15.89% | 15.89% | 15.60% | 16.20% | 0.31% |
| `rr_lyrae` | 22.99% | 23.00% | 23.40% | 22.54% | 0.45% |
| `solar_like` | 15.04% | 14.98% | 14.89% | 15.49% | 0.45% |
| `stable` | 21.72% | 21.79% | 21.99% | 21.13% | 0.59% |
