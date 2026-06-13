<!--
  Thank you for contributing to ASTRA!
  Please fill in every section below before requesting a review.
  PRs that are missing required sections will be marked "needs-work".
-->

## Description

<!-- Summarise what this PR does and why. Link the related issue(s) if applicable.
     Use "Closes #<issue-number>" to auto-close issues on merge. -->

**Closes:** #

### Type of Change

<!-- Check the type(s) that apply -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (existing behaviour changes in a backward-incompatible way)
- [ ] 🏗️ Refactor (code restructure with no functional change)
- [ ] 📊 Model / experiment update (new weights, architecture tweak, benchmark run)
- [ ] 📝 Documentation only
- [ ] 🔧 CI / infrastructure / tooling

---

## Changes Made

<!-- Bullet-point list of all significant changes introduced by this PR. -->

- 
- 

---

## Testing

### Tests Added / Updated

- [ ] New unit tests added (`tests/`)
- [ ] Existing tests updated to cover changed behaviour
- [ ] No tests required (documentation / config change only — explain below)

### Test Results

<!-- Paste the relevant test output, e.g. `pytest -v` summary, or CI badge/link. -->

```
# pytest output or CI link
```

### Model / Benchmark Changes (if applicable)

| Metric               | Before | After |
|----------------------|--------|-------|
| Test accuracy        |        |       |
| Parameters           |        |       |
| ECE (post-calibration)|       |       |

---

## Documentation

- [ ] Docstrings added or updated for all public functions / classes
- [ ] `README.md` updated (if user-facing behaviour changed)
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] Notebook / tutorial updated (if applicable)
- [ ] No documentation changes required

---

## Reproducibility & Data Integrity

- [ ] Dataset fingerprint (SHA-256) is **unchanged**, or a new fingerprint has been recorded and justified
- [ ] Random seeds are fixed (`torch.manual_seed`, `numpy.random.seed`) for any stochastic components
- [ ] Split hashes are deterministic and stored in experiment metadata JSON
- [ ] No raw data files are committed to the repository

---

## Zero-Hallucination Policy

> ASTRA enforces a strict zero-hallucination standard: every numerical claim, model result, and dataset statistic must be directly traceable to a reproducible experiment or a citable source.

- [ ] **I confirm** that all accuracy figures, parameter counts, and dataset statistics cited in this PR are directly traced to a reproducible experiment run or a citable external source
- [ ] **I confirm** that no speculative or unverified claims have been added to documentation, docstrings, or comments
- [ ] Results presented are from the **frozen test split only** (not from validation or training splits)

---

## Scientific Accuracy Check

- [ ] Any new stellar class definitions or transient taxonomies cite a peer-reviewed source (paper DOI or ADS bibcode)
- [ ] Light-curve preprocessing steps are physically motivated and documented
- [ ] Ground-truth labels are cross-matched against VSX / MAST and pass the zero-trust audit pipeline

---

## Reviewer Notes

<!-- Anything specific you want reviewers to focus on, tricky edge cases,
     or areas where you are uncertain and would appreciate extra scrutiny. -->

---

## Checklist Before Requesting Review

- [ ] Branch is up to date with `main`
- [ ] `pre-commit` hooks pass (linting, type checks)
- [ ] All CI checks are green
- [ ] Self-review completed — I have read through every changed line
