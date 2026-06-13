# ASTRA Dataset Documentation

> **Zero-Hallucination Policy**: All statistics derived from `data/dataset_summary.json`,
> `lineage.json`, `dataset_fingerprint.md`, and verified pipeline scripts.

---

## Dataset Identity

| Property | Value |
|----------|-------|
| **Name** | ASTRA TESS Variable Star Dataset |
| **Version** | 2.0 |
| **Total Stars** | 944 |
| **Dataset Hash** | `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58` |
| **Freeze Date** | 2026-06-12 |
| **Manifest SHA256** | `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58` |

The dataset fingerprint is cryptographically locked. Any modification to the processed
data directory will change this hash, immediately alerting researchers to data drift.

---

## Class Definitions

Defined in [`data/labels.py`](../data/labels.py) (single source of truth):

| Label | Class Name | Astronomical Description |
|-------|-----------|--------------------------|
| `0` | `rr_lyrae` | RR Lyrae pulsating variables — short-period Population II stars |
| `1` | `cepheid` | Classical & Type II Cepheids — primary cosmological distance indicators |
| `2` | `eclipsing_binary` | Eclipsing binary systems — period detectable via BLS |
| `3` | `solar_like` | Solar-like oscillators — acoustic p-mode pulsators |
| `4` | `stable` | Photometrically stable stars — reference non-variable population |

---

## Data Sources

### Primary Catalog Sources

| Source | Query Method | Content |
|--------|-------------|---------|
| **VSX (AAVSO)** | VizieR catalog `B/vsx` via `astroquery` | Variable star classifications, periods |
| **TESS/MAST** | `lightkurve` API | 2-minute cadence light curves |
| **TIC** | TESS Input Catalog | Stellar parameters (Tmag, Teff, logg, R) |
| **Published catalogs** | Literature | Asteroseismic solar-like oscillator targets |

All TIC IDs verified against MAST before inclusion. Stars without retrievable TESS
light curves are excluded at the preprocessing stage.

---

## Preprocessing Pipeline

**File:** [`pipeline/preprocess.py`](../pipeline/preprocess.py)

```
TIC ID
  │
  ├─ 1. Download TESS sector(s) via lightkurve.search_lightcurve()
  │      └─ Uses PDCSAP_FLUX (systematics-corrected)
  │
  ├─ 2. Quality filtering
  │      ├─ Remove NaN flux values
  │      ├─ Remove outliers: sigma clipping (σ=5, 3 iterations)
  │      └─ Apply TESS quality flag mask
  │
  ├─ 3. Sector stitching (multi-sector stars)
  │      └─ Normalize each sector to median=0, scale by MAD
  │
  ├─ 4. Savitzky-Golay detrending
  │      └─ Remove long-term systematics (window ~1/4 of baseline)
  │
  ├─ 5. BLS period search (for folded branch)
  │      ├─ Box Least Squares via astropy.timeseries.BoxLeastSquares
  │      └─ Best period used for phase folding
  │
  ├─ 6. Fixed-length arrays
  │      ├─ flux_1000.npy: 1000-point uniform resample (CNN input)
  │      └─ flux_200.npy: 200-point phase-folded/binned (transformer branch)
  │
  └─ 7. metadata.json: stores TIC ID, class label, processing stats
```

**Output structure** per star:
```
data/processed/TIC_<id>/
├── flux_1000.npy    # Primary input: shape (1000,), dtype float32
├── flux_200.npy     # Folded branch: shape (200,), dtype float32
└── metadata.json    # Star metadata and processing provenance
```

---

## Train / Validation / Test Splits

**File:** [`training/freeze_split.py`](../training/freeze_split.py)
**Split manifest files:** `phase6_train_ids.json`, `phase6_val_ids.json`, `phase6_test_ids.json`

Splits are **frozen** and **cryptographically hashed** to ensure reproducibility:

| Split | Count | Hash |
|-------|-------|------|
| **Train** | see `phase6_train_ids.json` | `5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0` |
| **Validation** | see `phase6_val_ids.json` | `c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3` |
| **Test** | see `phase6_test_ids.json` | `2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0` |
| **Root (all splits)** | — | `ebcdc44c3dba849579675369b1559c77e50b6fead06abd40d3fc187425a7d4e4` |

### Split Design Principles

1. **Group-aware**: Splits are performed by TIC ID, not by individual observations.
   No TIC ID appears in more than one split. This prevents data leakage from
   multi-sector stars.

2. **Stratified**: Class proportions are maintained across all splits.

3. **Frozen**: Once generated, splits are serialized to JSON and hashed.
   Training always loads from these frozen files — no re-splitting at runtime.

### Leakage Verification

Phase 6 split audit confirms:
- Zero TIC ID overlap between train/val/test
- Class distribution preserved within ±2% of catalog proportions
- No temporal leakage (TESS sector coverage not used as split criterion)

---

## Cross-Validation Protocol

5-fold stratified cross-validation with 3 random seeds:

| Seed | Purpose |
|------|---------|
| 42 | Primary seed (all results) |
| 100 | Stability check |
| 2026 | Final verification |

Results aggregated across 15 configurations (3 seeds × 5 folds).

---

## Data Integrity Verification

```bash
# Verify dataset fingerprint
python -c "
import hashlib, os, json

processed_dir = 'data/processed'
tic_dirs = sorted(os.listdir(processed_dir))
hasher = hashlib.sha256()

for tic_dir in tic_dirs:
    for fname in ['flux_1000.npy', 'flux_200.npy', 'metadata.json']:
        fpath = os.path.join(processed_dir, tic_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'rb') as f:
                hasher.update(f.read())

print(hasher.hexdigest())
# Expected: f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58
"
```

---

## Known Limitations

> [!WARNING]
> The following limitations are documented for scientific transparency.

1. **Solar-like class imbalance**: Solar-like oscillators require specialized
   asteroseismic analysis. Per-class F1 of 0.52 reflects genuine classification
   difficulty, not data error.

2. **TESS coverage**: Stars without retrievable TESS photometry are excluded.
   Coverage is uneven across sky positions due to TESS observing sectors.

3. **Class boundary ambiguity**: Some RR Lyrae / Cepheid and Solar-like / Stable
   boundaries are physically ambiguous in short TESS baselines.

4. **Single-observatory**: All light curves are from TESS only. Transfer to
   Kepler, ASAS-SN, or ZTF data is not validated.

---

## Catalog Pipeline

```bash
# Rebuild catalog from scratch (VSX + MAST query)
python pipeline/build_catalog.py

# Download and preprocess all stars
python pipeline/batch_process.py

# Verify data integrity after processing
python pipeline/dataset_audit.py
```

**Note:** Full catalog download requires internet access and may take several
hours depending on MAST API response times. The processed arrays are ~200MB total.
