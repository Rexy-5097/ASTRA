# ASTRA Phase 7C — Ground Truth Dataset Audit Report

This report documents a fresh filesystem scan and recomputation of the dataset attributes.

## 1. Directory & Files Verification

- **Processed Directories Count**: `944`
- **Missing required files**: `0`
- **Array Shape Mismatches**: `0`
- **NaN/Inf occurrences**: `0`

## 2. Recomputed Class Distribution

| Class Label | Count |
| :--- | :---: |
| `cepheid` | 230 |
| `rr_lyrae` | 217 |
| `stable` | 205 |
| `eclipsing_binary` | 150 |
| `solar_like` | 142 |

## 3. Light Curve Array Normalization

- **Average array mean**: `0.000000`
- **Average array standard deviation**: `1.000000`

## 4. Coordinate & Identity Duplication Audit

- **Duplicate TIC IDs count**: `0`
- **Duplicate coordinates (<=2.0 arcsec)**: `0`
- **Coordinate review pairs (2.0 to 10.0 arcsec)**: `0`
