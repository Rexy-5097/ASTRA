---
name: "🐛 Bug Report"
about: "Report a reproducible bug or unexpected behaviour in ASTRA"
title: "[BUG] <short description>"
labels: ["bug", "needs-triage"]
assignees: ""
---

<!--
  Thank you for taking the time to report a bug.
  Please fill in every section below so we can reproduce and fix the issue quickly.
  Remove any section that genuinely does not apply.
-->

## Description

<!-- A clear and concise description of what the bug is. -->

## Steps to Reproduce

<!-- Provide a minimal, self-contained sequence of steps that reliably triggers the bug. -->

1. 
2. 
3. 

**Minimal reproducible script (if applicable):**

```python
# paste your minimal reproduction script here
```

## Expected Behaviour

<!-- What did you expect to happen? -->

## Actual Behaviour

<!-- What actually happened? Include full error messages and tracebacks. -->

```
paste error / traceback here
```

## Environment

| Item                | Value                          |
|---------------------|--------------------------------|
| **Python version**  | e.g. 3.10.14                   |
| **PyTorch version** | e.g. 2.2.1+cu121               |
| **CUDA version**    | e.g. 12.1 / CPU only           |
| **OS / platform**   | e.g. Ubuntu 22.04 / macOS 14   |
| **ASTRA version / commit** | e.g. v1.0.0 / `git rev-parse --short HEAD` |
| **lightkurve version** | e.g. 2.4.2                  |

## Affected Component

<!-- Check all that apply -->

- [ ] Data pipeline (`src/data/`)
- [ ] Model — HybridTransformer (`src/models/hybrid_transformer*`)
- [ ] Model — CNN Dual-Branch (`src/models/cnn_dual*`)
- [ ] Training / cross-validation (`src/train*`)
- [ ] Calibration / uncertainty (`src/calibration/`)
- [ ] ONNX / TorchScript export (`src/export/`)
- [ ] Explainability / attention visualisation
- [ ] Web platform (`astra-platform/`)
- [ ] Other (describe below)

## Reproducibility

- [ ] Bug is **consistently reproducible** with the steps above
- [ ] Bug is **intermittent** — describe conditions when it appears

## Additional Context

<!-- Add any other context, screenshots, or log files here. -->
