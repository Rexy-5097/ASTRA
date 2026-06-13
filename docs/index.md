# ASTRA Documentation Index

Welcome to the ASTRA documentation. ASTRA (Automated Stellar Transient Recognition & Analysis)
is an end-to-end machine learning pipeline for classifying stellar variability from TESS light curves.

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [README](../README.md) | Start here — overview, quick start, results |
| [Architecture](architecture.md) | Model architectures (CNN, HybridTransformer) |
| [Dataset](dataset.md) | Data sources, preprocessing, split integrity |
| [Experiments](experiments.md) | Results, benchmarks, confusion matrices |
| [Reproducibility](reproducibility.md) | Step-by-step reproduction guide |
| [API Reference](api_reference.md) | Web platform API documentation |
| [Repository Health](repository_health.md) | Audit status and health metrics |

---

## Key Numbers (Verified)

| Metric | Value |
|--------|-------|
| Dataset size | 944 TESS stars |
| Dataset fingerprint | `f99b4b06...` |
| Best model | HybridTransformer (shared) |
| Test accuracy | 78.17% (95% CI: [71.13%, 85.21%]) |
| Macro F1 | 0.7677 |
| Ground truth audits | 8/8 PASS, 0 mismatches |

---

## Audit Trail

All scientific results have been independently verified:

- [`ground_truth_final_verdict.md`](../ground_truth_final_verdict.md) — Master audit verdict
- [`ground_truth_metrics.md`](../ground_truth_metrics.md) — Recomputed metrics with bootstrap CIs
- [`ground_truth_checkpoint_audit.md`](../ground_truth_checkpoint_audit.md) — Checkpoint integrity
- [`ground_truth_dataset_audit.md`](../ground_truth_dataset_audit.md) — Dataset integrity
- [`ground_truth_split_audit.md`](../ground_truth_split_audit.md) — Split leakage check
- [`ground_truth_calibration.md`](../ground_truth_calibration.md) — Calibration verification
- [`ground_truth_uncertainty.md`](../ground_truth_uncertainty.md) — MC Dropout AUROC
- [`ground_truth_reproducibility.md`](../ground_truth_reproducibility.md) — Hash verification

---

## Zero-Hallucination Policy

Every claim in this documentation is traceable to:
1. Source code in `pipeline/`, `training/`, or `data/`
2. Verified artifacts in `models/saved/`
3. Audit reports in the repository root
4. The `lineage.json` dataset provenance file

If you find a claim that cannot be traced to a verifiable source, please
[open an issue](https://github.com/soumyadebtripathy/ASTRA/issues).
