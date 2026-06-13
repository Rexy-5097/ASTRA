# ASTRA Architecture Reference

> **Zero-Hallucination Policy**: All parameter counts, layer dimensions, and specifications
> are derived directly from `training/models/hybrid_transformer.py`, `training/models/star_cnn.py`,
> and verified via `experiment_metadata.json`.

---

## Overview

ASTRA implements two primary model families for variable star classification from TESS light curves:

1. **StarCNN** — 1D Convolutional Neural Network (baseline)
2. **HybridTransformer** — Hybrid CNN + Transformer (best performing)

Both models process **1000-point resampled flux arrays** as input and output softmax probabilities
over 5 stellar variability classes.

---

## Input Representation

| Feature | Dimension | Description |
|---------|-----------|-------------|
| `flux_1000` | `(batch, 1, 1000)` | Resampled TESS photometric flux (primary branch) |
| `flux_200` | `(batch, 1, 200)` | Phase-folded/BLS-binned flux (secondary branch, HybridTransformer only) |

**Preprocessing pipeline:**
1. Download TESS sector light curves via `lightkurve`
2. Quality-flag filtering (NaN masking, sigma clipping)
3. Sector stitching and normalization
4. Savitzky-Golay detrending
5. BLS period search → phase folding → 200-point binning
6. Resample to 1000-point uniform grid

---

## Model 1: StarCNN

**File:** [`training/models/star_cnn.py`](../training/models/star_cnn.py)
**Verified parameter count:** ~1.14M (baseline; also used in early experiments)

### Architecture

```
Input: (B, 1, 1000)
│
├─ ConvBlock 1: Conv1d(1→32, k=15, s=2) → BN → ReLU → MaxPool(2)      → (B, 32, 249)
├─ ConvBlock 2: Conv1d(32→64, k=9, s=1) → BN → ReLU → MaxPool(2)      → (B, 64, 124)
├─ ConvBlock 3: Conv1d(64→128, k=7, s=1) → BN → ReLU → MaxPool(2)     → (B, 128, 61)
├─ ConvBlock 4: Conv1d(128→256, k=5, s=1) → BN → ReLU → MaxPool(2)    → (B, 256, 30)
├─ ConvBlock 5: Conv1d(256→256, k=3, s=1) → BN → ReLU → AdaptiveAvgPool(1) → (B, 256, 1)
│
├─ Flatten → (B, 256)
├─ Dropout(0.5)
├─ FC(256 → 512) → ReLU
├─ Dropout(0.3)
├─ FC(512 → 5)
└─ Output: (B, 5) logits
```

### Regularization
- BatchNorm after every convolution
- Dropout: 0.5 (before FC1), 0.3 (before FC2)
- Weight decay applied via AdamW optimizer

---

## Model 2: HybridTransformer (⭐ Best Model)

**File:** [`training/models/hybrid_transformer.py`](../training/models/hybrid_transformer.py)
**Verified parameter count (shared variant):** 1,373,701
**Verified parameter count (dual_aug CNN variant):** 1,043,333

### Transformer Encoder Layer

Custom Pre-LayerNorm encoder that returns attention weights for interpretability:

```python
class TransformerEncoderLayerCustom(nn.Module):
    # d_model=128, nhead=4, dim_feedforward=256, dropout=0.2
    
    forward(x):
        x2 = LayerNorm(x)
        attn_out, attn_weights = MultiheadAttention(x2, x2, x2)  # returns weights
        x = x + Dropout(attn_out)           # Pre-LN residual
        
        x2 = LayerNorm(x)
        ff = Linear(256→128)(ReLU(Linear(128→256)(x2)))
        x = x + Dropout(ff)                 # FFN residual
        
        return x, attn_weights
```

### Variant: `shared` (Best Performing)

```
Raw Input:   (B, 1, 1000) → CNN Encoder → (B, 128, T_raw)
Folded Input:(B, 1, 200)  → CNN Encoder → (B, 128, T_fold)
                                           ↓
                        Concatenate along time dim: (B, T_raw+T_fold, 128)
                                           ↓
                    Shared TransformerEncoder (2 layers × Pre-LN)
                                           ↓
                        GlobalAvgPool → (B, 128)
                                           ↓
                         Classifier Head → (B, 5)
```

**CNN Encoder (per branch):**
```
Conv1d(1→32, k=15, s=2) → BN → ReLU → MaxPool(2)
Conv1d(32→64, k=9, s=1) → BN → ReLU → MaxPool(2)
Conv1d(64→128, k=7, s=1) → BN → ReLU → MaxPool(2)
```

**Classifier Head:**
```
Linear(128 → 256) → GELU → Dropout(0.2) → Linear(256 → num_classes)
```

### All Supported Variants

| Variant | Description | Key Mechanism |
|---------|-------------|---------------|
| `shared` | ✅ Best | Single transformer processes concatenated raw+folded tokens |
| `separate` | Ablation | Independent transformers per branch, outputs concatenated |
| `cross` | Ablation | Folded tokens query raw tokens via cross-attention |
| `only` | Baseline | Transformer-only with linear patch embedding, no CNN |

---

## Dual-Branch CNN (`dual_aug`)

**Verified parameter count:** 1,043,333

```
Raw Input:   (B, 1, 1000) → StarCNN branches (shared weights) → feature_1
Folded Input:(B, 1, 200)  → Additional conv branch            → feature_2
                                           ↓
                        Concatenate: [feature_1, feature_2]
                                           ↓
                         Classifier Head → (B, 5)
```

---

## Training Configuration

All values from verified `experiment_metadata.json` and training scripts:

| Parameter | Value |
|-----------|-------|
| Optimizer | AdamW |
| Learning rate | 5×10⁻⁴ (default) |
| LR Schedule | CosineAnnealingLR |
| Batch size | 32 |
| Focal Loss γ | 2.0 |
| Focal Loss α | Inverse class frequency |
| Gradient clipping | 1.0 |
| Device | MPS (Apple Silicon M-series) |
| Seed | 42 (primary), also 100 and 2026 |
| CV folds | 5-fold stratified |
| Max epochs | ~100 (with early stopping on val accuracy) |

---

## Post-Training: Temperature Calibration

After training, temperature scaling is applied to calibrate softmax probabilities:

```python
# Files: training/calibration.py
# Optimal temperatures stored in:
#   models/saved/optimal_temperature_transformer_shared.txt
#   models/saved/optimal_temperature_cnn_dual.txt
```

**Purpose:** Reduces overconfidence of raw model softmax outputs, improving
reliability of uncertainty-aware predictions.

---

## Uncertainty Quantification: MC Dropout

```python
# File: training/uncertainty.py

def predict_with_uncertainty(model, x, T=50):
    model.train()  # Enable dropout at inference
    preds = torch.stack([model(x) for _ in range(T)])
    mean = preds.mean(0)
    entropy = -(mean * mean.log()).sum(-1)  # Predictive entropy
    return mean, entropy
```

**T=50 Monte Carlo forward passes** at inference time.
AUROC on uncertainty-based selective prediction verified in Phase 7C audit.

---

## Explainability

```python
# Files: training/models/explainable_wrapper.py
#        training/export_explainability_model.py
#        training/explain_inference.py
```

The `ExplainableWrapper` exposes intermediate attention weight tensors,
enabling attention-map overlays on light curve plots. ONNX export:
`models/saved/best_star_transformer_shared_explain.onnx`

---

## Export Formats

| Format | File | Description |
|--------|------|-------------|
| PyTorch state_dict | `best_star_transformer_shared.pt` | Primary checkpoint |
| ONNX | `best_star_transformer_shared.onnx` | Cross-platform inference |
| TorchScript | `best_star_transformer_shared.torchscript` | Production deployment |
| ONNX (explainability) | `best_star_transformer_shared_explain.onnx` | With attention outputs |

All checkpoints include `checkpoint_sha256` in `experiment_metadata.json` for integrity verification.

---

## Integrity Verification

```python
import hashlib
import json

with open("models/saved/experiment_metadata.json") as f:
    meta = json.load(f)

sha256 = meta["shared"]["checkpoint_sha256"]
# Verify: bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388

with open("models/saved/best_star_transformer_shared.pt", "rb") as f:
    actual = hashlib.sha256(f.read()).hexdigest()

assert actual == sha256, "Checkpoint integrity check FAILED"
print("✅ Checkpoint integrity verified")
```
