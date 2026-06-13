# Changelog

All notable changes to ASTRA are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

> Changes staged for the next release will appear here.

---

## [1.0.0] — 2026-06-13

### Added

#### Models & Architecture
- **HybridTransformer (shared variant)** — primary production model; 1,373,701 parameters; 78.17 % test accuracy on the 944-star TESS benchmark
- **CNN Dual-Branch** — secondary production model; 1,043,333 parameters; 78.17 % test accuracy
- Temperature calibration via MC (Maximum Calibration) scaling for both HybridTransformer and CNN Dual-Branch architectures
- MC Dropout uncertainty quantification layer, enabling per-prediction epistemic uncertainty estimates

#### Deployment & Export
- ONNX export pipeline for hardware-agnostic inference
- TorchScript export for PyTorch-native deployment without Python runtime
- Explainability wrapper with attention-map visualization for HybridTransformer attention heads

#### Web Platform
- Full-stack web platform at `astra-platform/` built with Next.js and Three.js
- Interactive 3-D sky visualization and light-curve inspection UI

#### Validation & Reproducibility
- 5-fold cross-validation with 3 independent random seeds (42, 100, 2026)
- Dataset fingerprint lock — SHA-256 hash integrity verification for the canonical TESS dataset split
- Zero-trust ground truth audit — all 8 audit checks **PASS**
- Full experiment reproducibility artefacts: deterministic split hashes and experiment metadata JSON files

#### Dataset
- 944-star verified TESS dataset spanning 5 transient classes, frozen at Phase 6 dataset fingerprint v2.0

---

## [0.9.0] — 2026-06-12

### Added
- Four Transformer architectural variants: **separate**, **shared**, **cross**, and **only** attention strategies
- Phase 7 full benchmark suite comparing all model variants on the frozen test split
- Phase 8 explainability audit — attention-head attribution analysis across all five stellar classes
- Calibration strategy report documenting reliability diagrams and Expected Calibration Error (ECE) before/after temperature scaling

---

## [0.8.0] — 2026-06-12

### Added
- Phase 6 dataset freeze: canonical train / validation / test split with deterministic seed and persisted indices
- Metadata repair pipeline — corrected missing and malformed class labels in the TESS catalogue
- Integrity verification step: row-count and class-distribution checks gate all downstream experiments
- Dataset fingerprint v2.0 — SHA-256 hash of the frozen split stored in `data/fingerprint.json`

---

## [0.1.0] — 2026-05-25

### Added
- Initial 1D-CNN baseline implementation for single-branch light-curve classification
- VSX + MAST catalogue ingestion pipeline for source cross-matching and label assignment
- `lightkurve`-based preprocessing pipeline: gap filling, normalisation, and sigma-clipping
- Focal loss function with inverse-frequency class weighting to handle severe class imbalance across transient types

---

## Version Summary

| Version | Date       | Milestone                              |
|---------|------------|----------------------------------------|
| 1.0.0   | 2026-06-13 | Production release — dual-model v1     |
| 0.9.0   | 2026-06-12 | Transformer variants + benchmark suite |
| 0.8.0   | 2026-06-12 | Dataset freeze + integrity audit       |
| 0.1.0   | 2026-05-25 | Initial 1D-CNN + data pipeline         |

[Unreleased]: https://github.com/soumyadebtripathy/ASTRA/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/soumyadebtripathy/ASTRA/compare/v0.1.0...v0.8.0
[0.1.0]: https://github.com/soumyadebtripathy/ASTRA/releases/tag/v0.1.0
