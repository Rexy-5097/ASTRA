# ASTRA Metadata Integrity Summary Report

## 1. Directory and File Audits
- **Total directories found on disk:** 944
- **Missing files per star:** 0 (all 5 required files present in all directories)
- **Corrupt files:** 0

## 2. Repaired Dataset Profile
- **Total star count:** 944
### Class counts
| Class | Count |
| :--- | :--- |
| `cepheid` | 230 |
| `eclipsing_binary` | 150 |
| `rr_lyrae` | 217 |
| `solar_like` | 142 |
| `stable` | 205 |

### Period source counts
- **Catalog period source:** 597
- **BLS period source:** 347

- **Scientific Manifest Checksum (SHA256):** `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58`

## 3. Final Verdict
### **DATASET_STATUS: GO**
- **Evidence:** All metadata files are fully repaired, self-consistent, and hash-verified. No coordinate leaks, duplicate TICs, or physical overlaps exist. The dataset is fully validated and ready for retraining.
