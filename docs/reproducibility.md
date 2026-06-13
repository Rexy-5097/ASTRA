# Reproducibility Guide

This document enables any researcher to reproduce all ASTRA results from scratch,
in compliance with the **zero-hallucination policy** — every step is traceable
to source code and verified artifacts.

---

## Prerequisites

| Requirement | Verified Version |
|-------------|:---:|
| macOS | Apple Silicon (M-series) |
| Python | 3.12 |
| PyTorch | 2.12.0 |
| MPS backend | ✅ Required for exact numerical parity |

> [!NOTE]
> MPS (Apple Silicon GPU) produces numerically identical results to the original
> training run. CPU fallback is supported but may produce slightly different
> floating-point results due to different computation order.

---

## Step 0: Clone & Environment

```bash
git clone https://github.com/soumyadebtripathy/ASTRA.git
cd "ASTRA — Automated Stellar Transient Recognition & Analysis"

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

**Verify installation:**
```bash
python -c "import torch; print(torch.backends.mps.is_available())"
# Expected: True (on Apple Silicon)
```

---

## Step 1: Verify Dataset Integrity

Before training, verify the dataset fingerprint:

```bash
python -c "
import hashlib, os, json

processed_dir = 'data/processed'
tic_dirs = sorted([d for d in os.listdir(processed_dir) if d.startswith('TIC_')])
hasher = hashlib.sha256()

for tic_dir in tic_dirs:
    for fname in sorted(['flux_1000.npy', 'flux_200.npy', 'metadata.json']):
        fpath = os.path.join(processed_dir, tic_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'rb') as f:
                hasher.update(f.read())

actual = hasher.hexdigest()
expected = 'f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58'
assert actual == expected, f'Dataset hash mismatch: {actual}'
print('✅ Dataset integrity: VERIFIED')
print(f'   Hash: {actual}')
"
```

---

## Step 2: Rebuild Dataset (Optional)

If you want to rebuild from MAST/VSX from scratch (requires internet + hours):

```bash
# Build catalog
python pipeline/build_catalog.py

# Preprocess all stars
python pipeline/batch_process.py

# Audit processed data
python pipeline/dataset_audit.py
```

---

## Step 3: Verify Split Integrity

```bash
python -c "
import hashlib, json

for split, fname in [('train', 'phase6_train_ids.json'),
                      ('val',   'phase6_val_ids.json'),
                      ('test',  'phase6_test_ids.json')]:
    with open(fname, 'rb') as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print(f'{split}: {h}')

# Expected hashes (from experiment_metadata.json):
# train: 5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0
# val:   c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3
# test:  2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0
"
```

---

## Step 4: Train Primary Model

```bash
# HybridTransformer (shared) — primary result
python training/train_transformer.py \
    --variant shared \
    --seed 42

# CNN Dual Branch — secondary result
python training/train_cnn.py \
    --seed 42
```

**Expected outputs:**
- `models/saved/best_star_transformer_shared.pt`
- `models/saved/training_history_transformer_shared.json`
- `models/saved/training_curves_transformer_shared.png`

---

## Step 5: Reproduce Test Metrics

```bash
# Evaluate on held-out test set
python training/predict.py --variant shared

# Verify checkpoint integrity
python -c "
import hashlib, json

with open('models/saved/experiment_metadata.json') as f:
    meta = json.load(f)

sha256 = meta['shared']['checkpoint_sha256']
with open('models/saved/best_star_transformer_shared.pt', 'rb') as f:
    actual = hashlib.sha256(f.read()).hexdigest()

if actual == sha256:
    print('✅ Checkpoint verified:', sha256)
else:
    print('❌ Hash mismatch!')
    print('Expected:', sha256)
    print('Actual:  ', actual)
"
```

**Expected test accuracy: 78.17%**
**Expected Macro F1: 0.7677**

---

## Step 6: Run Cross-Validation

```bash
# 5-fold CV across 3 seeds (long-running)
python training/cross_validate.py --seed 42
python training/cross_validate.py --seed 100
python training/cross_validate.py --seed 2026
```

Results stored in `fold_metrics.csv`.

---

## Step 7: Calibration

```bash
python training/calibration.py --variant shared
python training/calibration.py --variant dual_aug

# Optimal temperatures saved to:
# models/saved/optimal_temperature_transformer_shared.txt
# models/saved/optimal_temperature_cnn_dual.txt
```

---

## Step 8: Uncertainty Quantification

```bash
python training/uncertainty.py --variant shared
```

---

## Step 9: Export Models

```bash
# ONNX + TorchScript export
python training/export_model.py --variant shared

# Explainability model
python training/export_explainability_model.py
```

---

## Automated Test Suite

```bash
# Run unit tests
python -m pytest tests/ -v

# Run pipeline integration test
python tests/test_phase6_pipeline.py
```

---

## Numerical Reproducibility Notes

| Factor | Impact | Mitigation |
|--------|--------|-----------|
| MPS vs CPU | Minor float differences | Use MPS for exact parity |
| PyTorch version | Potential kernel differences | Pin to 2.12.0 |
| Seed | Critical | seed=42 for all primary results |
| Data order | Fixed by frozen split JSON | Load from split files only |

Setting `torch.manual_seed(42)` and `numpy.random.seed(42)` before any
training operation ensures deterministic behavior on the same hardware.

---

## Verified Artifact Registry

All experiments produce a self-contained metadata file:

```json
// models/saved/experiment_metadata.json
{
  "shared": {
    "variant": "shared",
    "seed": 42,
    "device": "mps",
    "torch_version": "2.12.0",
    "parameter_count": 1373701,
    "dataset_fingerprint_hash": "f99b4b06...",
    "split_hash_root": "ebcdc44c...",
    "checkpoint_sha256": "bf374ce4...",
    "timestamp": "2026-06-13T00:35:13Z"
  }
}
```

This file is the **ground truth** for all reproducibility verification.
