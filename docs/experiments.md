# ASTRA Experiments & Results

> **Zero-Hallucination Policy**: All metrics below are recomputed and verified
> in the Phase 7C Ground Truth Audit (`ground_truth_metrics.md`).
> Zero mismatches were found across all 8 audit checks.

---

## Experiment Overview

ASTRA conducted a systematic model comparison across multiple architectures,
training configurations, and evaluation protocols. All experiments share
the same frozen dataset (v2.0, 944 stars) and identical train/val/test splits.

---

## Primary Results: Test Set Performance

> [!IMPORTANT]
> The following metrics are **VERIFIED** via independent recomputation.
> They were validated in the Phase 7C Ground Truth Audit with 0 mismatches.

### Test Accuracy & F1 (95% Bootstrap Confidence Intervals)

| Architecture | Variant | Test Accuracy | 95% CI | Macro F1 | 95% CI |
|-------------|---------|:---:|:---:|:---:|:---:|
| **HybridTransformer** | shared ⭐ | **78.17%** | [71.13%, 85.21%] | **0.7677** | [0.6944, 0.8320] |
| **CNN Dual Branch** | dual_aug | 78.17% | [71.83%, 84.51%] | 0.7635 | [0.6923, 0.8301] |
| HybridTransformer | cross | 74.47% | — | — | — |
| HybridTransformer | separate | 75.18% | — | — | — |
| HybridTransformer | only | 73.05% | — | — | — |

> **Note on tied test accuracy**: Both `shared` and `dual_aug` achieve 78.17% on
> identical test samples. The Transformer Shared variant is preferred as the
> primary model due to marginally higher Macro F1 and per-class performance
> on Cepheid and Eclipsing Binary classes.

---

## Per-Class F1 Scores (Primary Models)

| Class | HybridTransformer (shared) | CNN Dual Branch |
|-------|:---:|:---:|
| RR Lyrae | **0.9394** | 0.9394 |
| Cepheid | **0.8108** | 0.7838 |
| Eclipsing Binary | **0.9091** | 0.8696 |
| Solar-like ⚠️ | 0.5238 | 0.5128 |
| Stable | 0.6552 | **0.7119** |

> [!WARNING]
> **Solar-like (class 3) performance** is markedly lower (F1 ≈ 0.52).
> This is an **EXPERIMENTAL** result. Solar-like oscillators present genuine
> classification challenges due to: (1) short TESS baselines insufficient
> to resolve low-frequency p-mode oscillations, (2) morphological similarity
> to stable stars in short-cadence data, (3) class boundary ambiguity.
> This is not a training failure but a scientifically expected limitation.

---

## Validation Accuracy (Best Checkpoints)

| Architecture | Variant | Best Val Accuracy |
|-------------|---------|:---:|
| HybridTransformer | shared | **85.82%** |
| CNN Dual Branch | dual_aug | 85.11% |

---

## Full Model Comparison (Test Set)

From `phase7_benchmark_report.md` and `phase7_testset_benchmark.md`:

| Architecture | Variant | Params | Test Acc | Macro F1 | Weighted F1 |
|-------------|---------|:---:|:---:|:---:|:---:|
| HybridTransformer | shared | 1,373,701 | 78.17% | 0.7677 | 0.7784 |
| CNN Dual | dual_aug | 1,043,333 | 78.17% | 0.7635 | 0.7756 |
| HybridTransformer | separate | ~1.37M | 75.18% | — | — |
| HybridTransformer | cross | ~1.37M | 74.47% | — | — |
| HybridTransformer | only | ~0.9M | 73.05% | — | — |

---

## Cross-Validation Results

5-fold stratified CV across 3 seeds. CSV data in `fold_metrics.csv`.

| Seed | Metric | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Mean |
|------|--------|--------|--------|--------|--------|--------|------|
| 42 | Val Acc | — | — | — | — | — | see fold_metrics.csv |
| 100 | Val Acc | — | — | — | — | — | see fold_metrics.csv |
| 2026 | Val Acc | — | — | — | — | — | see fold_metrics.csv |

Confusion matrices for all 15 configurations are stored in
`models/saved/confusion_matrix_seed{seed}_fold{k}.png`.

---

## Temperature Calibration

Post-training temperature scaling reduces overconfidence:

| Model | Optimal Temperature |
|-------|:---:|
| HybridTransformer (shared) | see `models/saved/optimal_temperature_transformer_shared.txt` |
| CNN Dual Branch | see `models/saved/optimal_temperature_cnn_dual.txt` |

After calibration, Expected Calibration Error (ECE) is significantly reduced.
Reliability diagrams shown in `calibration_report.md`.

---

## Confusion Matrix Analysis

Critical failure mode analysis (from `ground_truth_metrics.md`):

| Failure Mode | CNN Dual Count | Transformer Shared Count |
|--------------|:---:|:---:|
| RR Lyrae → Cepheid | **0** | **0** |
| Cepheid → RR Lyrae | 1 | **0** |
| Eclipsing Binary → Cepheid | 1 | **0** |
| Solar-like → Stable | 3 | 5 |

The most scientifically important confusion (RR Lyrae ↔ Cepheid) is **zero**
for the Transformer Shared model — these classes are most easily conflated
in period-luminosity space.

---

## Reproducibility

All experiments are fully reproducible via frozen splits and recorded seeds:

```bash
# Reproduce primary result (HybridTransformer shared, seed=42)
python training/train_transformer.py \
    --variant shared \
    --seed 42 \
    --splits-root . \
    --epochs 100

# Verify against frozen metadata
python training/inference_consistency.py
```

**Integrity chain:**
1. Dataset hash: `f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58`
2. Split hash root: `ebcdc44c3dba849579675369b1559c77e50b6fead06abd40d3fc187425a7d4e4`
3. Checkpoint SHA256 (shared): `bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388`

---

## Uncertainty Quantification

MC Dropout (T=50) applied at inference time. Results from `ground_truth_uncertainty.md`:

- High-entropy predictions correlate with Solar-like class boundary cases
- AUROC on uncertainty-based selective prediction: verified in Phase 7C audit
- Uncertainty histograms: `entropy_histograms.png`, `subgroup_uncertainty_boxplots.png`

---

## Explainability

Attention maps from the TransformerEncoder layers highlight which time-series
regions drive classification decisions. Implementation in:

- `training/models/explainable_wrapper.py`
- `training/explain_inference.py`
- `training/visualize_attention.py`

ONNX explainability export: `models/saved/best_star_transformer_shared_explain.onnx`

---

## Audit Trail

All results have been independently verified:

| Audit | Target | Status |
|-------|--------|:---:|
| Task 0 | Dataset Fingerprint Hash Lock | ✅ PASS |
| Audit A | Processed Dataset Integrity & Duplicates | ✅ PASS |
| Audit B | Train/Val/Test Leakage & Stratification | ✅ PASS |
| Audit C | Checkpoint state_dict Key Alignment | ✅ PASS |
| Audit D | Validation and Test Metrics Recomputation | ✅ PASS |
| Audit E | Temperature Calibration Optimization | ✅ PASS |
| Audit F | MC Dropout Uncertainty AUROC | ✅ PASS |
| Audit G | Attention Dimensionality Verification | ✅ PASS |
| Audit H | Reproducibility JSON hashes | ✅ PASS |

**Total mismatches: 0**

Source: `ground_truth_final_verdict.md`
