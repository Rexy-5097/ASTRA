# Contributing to ASTRA

**ASTRA — Automated Stellar Transient Recognition & Analysis**

Thank you for your interest in contributing. ASTRA is a real, end-to-end
machine-learning pipeline that classifies TESS light curves into five stellar
variability classes. Because the project makes claims about real astronomical
objects and trained model performance, every contribution carries scientific
weight. Please read this guide fully before opening a pull request.

---

## Table of Contents

1. [Code of Conduct](#1-code-of-conduct)
2. [Reporting Issues](#2-reporting-issues)
3. [Development Setup](#3-development-setup)
4. [Repository Layout](#4-repository-layout)
5. [Branching Strategy](#5-branching-strategy)
6. [Pull Request Checklist](#6-pull-request-checklist)
7. [Zero-Hallucination Policy](#7-zero-hallucination-policy)
8. [Scientific Contribution Guidelines](#8-scientific-contribution-guidelines)
9. [Testing Requirements](#9-testing-requirements)
10. [Code Style](#10-code-style)
11. [Web Platform (`astra-platform/`)](#11-web-platform-astra-platform)
12. [Licensing](#12-licensing)

---

## 1. Code of Conduct

All contributors are expected to uphold the [Code of Conduct](CODE_OF_CONDUCT.md).
Participation in this project — including issues, pull requests, code review,
and discussions — constitutes acceptance of that document.

---

## 2. Reporting Issues

### Bug Reports

Open a GitHub Issue and include:

- **Environment:** macOS version, Python version (project targets Python 3.11+),
  PyTorch version, device (`mps` / `cpu`).
- **Reproduction steps:** The exact command(s) that triggered the bug.
- **Expected vs. actual behaviour:** Paste relevant log output or tracebacks.
- **Affected file(s):** e.g., `pipeline/preprocess.py`, `training/train_cnn.py`.

> **Note:** ASTRA is developed on Apple Silicon (M-series, MPS backend). If you
> can reproduce the issue on CPU as well, please confirm this — it helps triage.

### Scientific Inaccuracies

If you discover an incorrect class label, a mislabelled TIC ID, an erroneous
period assignment, or any claim that contradicts published photometric data:

1. Open an Issue with the label **`scientific-inaccuracy`**.
2. Cite the authoritative source (VSX entry, MAST data product, peer-reviewed
   paper with DOI, or SIMBAD record).
3. Include the TIC ID, the current value in the codebase, and the correct value
   with a reference.

Suspected dataset-integrity issues should also reference the relevant audit
document (`ground_truth_*.md`, `phase6_*.md`, or `phase7_*.md`) if one exists.

---

## 3. Development Setup

### Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.11 |
| macOS | 13 Ventura (Apple Silicon recommended) |
| PyTorch | 2.0 (MPS backend; CPU fallback supported) |
| Node.js | 18 LTS (web platform only) |

### Clone and Install

```bash
# 1. Clone the repository
git clone <repository-url>
cd "ASTRA — Automated Stellar Transient Recognition & Analysis"

# 2. Create an isolated virtual environment
python3.11 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish

# 3. Install all Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

The `requirements.txt` pins the following core packages:

```
torch>=2.0
numpy>=1.24
scipy>=1.10
astropy>=5.3
lightkurve>=2.4
astroquery>=0.4.6
matplotlib>=3.7
scikit-learn>=1.3
tqdm>=4.65
```

### Verify Installation

```bash
python - <<'EOF'
import torch, numpy, astropy, lightkurve
print("PyTorch:", torch.__version__, "| MPS:", torch.backends.mps.is_available())
print("NumPy:", numpy.__version__)
print("Astropy:", astropy.__version__)
print("lightkurve:", lightkurve.__version__)
EOF
```

### Web Platform (optional)

```bash
cd astra-platform
npm install
npm run dev       # http://localhost:3000
```

---

## 4. Repository Layout

```
ASTRA/
├── data/
│   ├── labels.py              # CLASS_NAMES / NAME_TO_LABEL — single source of truth
│   ├── catalog_full.json      # 944-star TESS catalog with TIC IDs
│   ├── dataset_summary.json   # Per-class counts and catalog statistics
│   └── processed/             # Per-star preprocessed arrays (TIC_<id>/)
│       └── TIC_<id>/
│           ├── flux_1000.npy        # 1 000-point resampled flux (CNN input)
│           ├── flux_200.npy         # 200-point raw downsample
│           ├── folded_flux_1000.npy # Phase-folded at selected period
│           ├── folded_flux_200.npy  # Phase-folded, 200-point binned
│           └── metadata.json        # Star-level processing metadata
├── pipeline/                  # Data acquisition and preprocessing
│   ├── build_catalog.py
│   ├── preprocess.py
│   ├── batch_process.py
│   ├── dataset_audit.py
│   ├── download_manager.py
│   ├── freeze_phase6_splits.py
│   ├── phase6_utils.py
│   └── ...
├── training/                  # Model training and evaluation
│   ├── dataset.py             # PyTorch Dataset, group-aware splits
│   ├── focal_loss.py          # Focal loss for class imbalance
│   ├── train_cnn.py           # 1D CNN training loop
│   ├── train_transformer.py   # Transformer training loop
│   ├── predict.py
│   ├── calibration.py
│   ├── uncertainty.py
│   └── models/
│       └── star_cnn.py        # 1D CNN (~1.14 M parameters)
├── models/
│   └── saved/                 # Checkpoints (.pt), ONNX exports, metadata
│       ├── experiment_metadata.json   # SHA-256 hashes for all checkpoints
│       └── ...
├── tests/
│   └── test_phase6_pipeline.py
├── astra-platform/            # Next.js 16 web dashboard
│   ├── src/
│   ├── package.json
│   └── ...
├── requirements.txt
├── CONTRIBUTING.md            # <- this file
├── CODE_OF_CONDUCT.md
└── SECURITY.md
```

---

## 5. Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, always-passing. Protected. Never commit directly. |
| `feature/<short-description>` | New features (e.g., `feature/add-eb-subtype`) |
| `fix/<short-description>` | Bug fixes (e.g., `fix/bls-period-nan-guard`) |
| `science/<short-description>` | Dataset, label, or architecture changes |
| `docs/<short-description>` | Documentation-only changes |

**Workflow:**

```
main
 └─ feature/my-feature      <- branch off main
     └─ (commits)
     └─ PR -> main           <- squash-merge after review
```

- Always branch off the latest `main`.
- Keep branches short-lived (prefer < 2 weeks).
- Rebase on `main` before opening a PR to keep a clean history.

---

## 6. Pull Request Checklist

Before marking your PR as ready for review, confirm **every** item:

- [ ] Branched from and rebased on the latest `main`
- [ ] PR title is descriptive and uses imperative mood
  (`Add solar-like subclass` not `Added solar-like subclass`)
- [ ] All new Python code is PEP 8 compliant and includes Google-style docstrings
- [ ] Tests pass: `python -m pytest tests/test_phase6_pipeline.py -v`
- [ ] No new metrics, accuracy figures, or scientific claims are introduced
  without a traceable source (see Zero-Hallucination Policy below)
- [ ] Any new checkpoint (`.pt` file) is accompanied by an updated
  `models/saved/experiment_metadata.json` entry with a `checkpoint_sha256` field
- [ ] Any change to `data/labels.py` (CLASS_NAMES / NAME_TO_LABEL) is
  reflected across all dependent modules and test fixtures
- [ ] Web platform changes (`astra-platform/`): `npm run lint` passes with
  zero errors
- [ ] No secrets, API keys, or personally identifiable information committed
- [ ] PR description explains *why* the change is needed, not just *what* it does

---

## 7. Zero-Hallucination Policy

> **Every quantitative claim in this repository must be traceable to a real
> artifact produced by the actual codebase or to a citable external source.**

This policy applies to all contributors — human and AI-assisted alike.

### What this means in practice

| Allowed | Prohibited |
|---|---|
| Reporting an accuracy figure that appears in a `classification_report_*.txt` file in `models/saved/` | Inventing or estimating a figure not backed by an artifact |
| Citing a VSX entry or a peer-reviewed DOI for a stellar classification | Describing a star class behaviour from general knowledge without a reference |
| Adding a SHA-256 hash that was computed from the actual checkpoint file | Copy-pasting a hash from a different run or estimating it |
| Describing a parameter count that matches `experiment_metadata.json` | Rounding a parameter count or guessing |

### For AI-assisted contributions

If you used an AI coding assistant to generate or edit code, you are personally
responsible for verifying every factual claim, metric, and hash in the diff.
Commits that introduce unverifiable claims will be reverted without discussion.

---

## 8. Scientific Contribution Guidelines

### Adding a New Stellar Variability Class

ASTRA currently classifies five classes defined in `data/labels.py`:

| Label | Class |
|---|---|
| 0 | `rr_lyrae` |
| 1 | `cepheid` |
| 2 | `eclipsing_binary` |
| 3 | `solar_like` |
| 4 | `stable` |

To propose a new class:

1. Open an Issue with label **`new-class`** before writing any code.
2. Justify the class with at least one citable external source (VSX, SIMBAD,
   a published asteroseismic catalog, or a peer-reviewed paper).
3. Demonstrate that the class is meaningfully separable from existing classes
   using TESS photometry — include a confusion-matrix excerpt or t-SNE plot.
4. Provide a minimum of 50 verified TIC IDs (confirmed in MAST) for the
   new class.
5. Update `data/labels.py`, all training scripts, and `tests/test_phase6_pipeline.py`
   class-enumeration fixtures atomically.

### Adding a New Model Architecture

1. Add the architecture under `training/models/` following the naming
   convention of `star_cnn.py`.
2. Register a new training entry point under `training/` (e.g.,
   `train_<architecture>.py`), following the structure of `train_transformer.py`.
3. Run a full training cycle and save output artifacts:
   - Checkpoint: `models/saved/best_star_<architecture>.pt`
   - Metadata: `models/saved/experiment_metadata_<architecture>.json`
     (must include `checkpoint_sha256`, `parameter_count`, `seed`, `device`,
     `torch_version`, `dataset_fingerprint_hash`, `split_hashes`, `timestamp`)
   - Training history: `models/saved/training_history_<architecture>.json`
   - Confusion matrix: `models/saved/confusion_matrix_<architecture>.png`
4. Run the full benchmark against existing architectures and include results
   in your PR description.

### Modifying the Preprocessing Pipeline

Changes to `pipeline/preprocess.py` or `pipeline/phase6_utils.py` can silently
invalidate the entire preprocessed dataset. Any such change **must**:

- Pass `tests/test_phase6_pipeline.py` in full.
- Document the change in a `ground_truth_*.md` audit file.
- Increment the `preprocessing_version` field in all regenerated `metadata.json`
  files (or justify why reprocessing is not required).

---

## 9. Testing Requirements

The test suite lives in `tests/test_phase6_pipeline.py` and covers:

- Period-selection logic (`_select_period`)
- Flux-array shape correctness (`_resample_normalized`, `_phase_bin_normalized`)
- Data-cleanup behaviour (`_cleanup_star_dir`)
- Download-manager gating (`_row_is_processable`, `download_phase6`)
- Duplicate-group assignment (`assign_duplicate_groups`)
- End-to-end audit and freeze on a synthetic Phase 6 dataset
- Training guard (refuses unverified Phase 6 paths)
- Array-hash stability (`array_content_hash`)
- Raw-file hash sensitivity (`sha256_file`)

### Running the Tests

```bash
# From the repository root, with .venv activated:
python -m pytest tests/test_phase6_pipeline.py -v
```

All nine test cases must pass with **zero failures and zero errors** before
a PR may be merged.

> **Tip:** Run with `-s` to see stdout from the pipeline during test execution:
> `python -m pytest tests/test_phase6_pipeline.py -v -s`

### Adding New Tests

- New pipeline functionality must have a corresponding unit test.
- Tests must be self-contained: use `tempfile.TemporaryDirectory()` for any
  filesystem writes; do not depend on the contents of `data/processed/`.
- Follow the `unittest.TestCase` style already used in `test_phase6_pipeline.py`.

---

## 10. Code Style

### Python

- **Standard:** PEP 8 strictly.
- **Maximum line length:** 99 characters.
- **Docstrings:** Google style for all public functions, classes, and modules.
- **Type hints:** Required for all new function signatures.

Example:

```python
def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        Lowercase hexadecimal SHA-256 digest string.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
```

- **Imports:** Standard library -> third-party -> local, each group separated
  by a blank line.
- **No bare `except:`** — always catch specific exceptions.
- **No `print()` in library code** — use `logging` or `tqdm`.

### TypeScript / Next.js (`astra-platform/`)

See the Web Platform section below.

---

## 11. Web Platform (`astra-platform/`)

The `astra-platform/` directory contains a **Next.js 16** application (React 19,
TypeScript, Tailwind CSS 4) that serves as the ASTRA Stellar Intelligence
dashboard.

### Tech Stack

| Layer | Library / Version |
|---|---|
| Framework | Next.js 16.2.9 (App Router) |
| UI | React 19.2.4 + shadcn/ui + Base UI |
| Visualisation | Recharts 3, Three.js / React Three Fiber |
| State | Zustand 5, TanStack Query 5 |
| ML inference | `onnxruntime-node` (runs ONNX exports from `models/saved/`) |
| Styling | Tailwind CSS 4, Framer Motion 12 |
| Linting | ESLint 9 with `eslint-config-next` |

### API Endpoints

The platform exposes eight Next.js Route Handler endpoints (all verified
end-to-end in `phase8_api_audit.md`):

| Endpoint | Method | Description |
|---|---|---|
| `/api/stars` | GET | Search 944-star database with pagination and class/source/split filters |
| `/api/stars/[id]` | GET | Single star coordinate metadata and observations |
| `/api/lightcurve/[id]` | GET | 1 000-point raw and 200-point folded flux arrays |
| `/api/osint/[id]` | GET | Gaia DR3, SIMBAD, and ASAS-SN cross-match dossier |
| `/api/metrics` | GET | Model parameters, temperature scalings, ECE histograms, checkpoint hashes |
| `/api/health` | GET | Live filesystem and checksum health (READY / DEGRADED / BLOCKED) |
| `/api/explain/[id]` | GET | ONNX explainability inference with attention weights [250, 250] |
| `/api/upload` | POST | Custom photometry upload -> detrending -> ONNX prediction |

### Frontend Development Workflow

```bash
cd astra-platform

# Install dependencies
npm install

# Start development server
npm run dev          # http://localhost:3000

# Type-check
npx tsc --noEmit

# Lint
npm run lint
```

### Code Style (TypeScript)

- **ESLint** config: `eslint-config-next` (see `eslint.config.mjs`).
- `npm run lint` must pass with zero warnings or errors.
- Components go under `src/` following the existing App Router conventions.
- Do not introduce new third-party dependencies without discussion in an Issue.
- The ONNX model files loaded at runtime must match the hashes in
  `models/saved/experiment_metadata.json` — see [SECURITY.md](SECURITY.md)
  for the verification procedure.

---

## 12. Licensing

By submitting a pull request you agree that your contribution will be licensed
under the same license as the rest of this project. Ensure that any data files,
catalog extracts, or figures you include are either (a) produced entirely by the
ASTRA pipeline from publicly available TESS/MAST data, or (b) covered by a
compatible open license with attribution provided in the PR description.

---

*Questions? Open a GitHub Discussion or an Issue with the label `question`.*
