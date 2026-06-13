# Security Policy

**ASTRA — Automated Stellar Transient Recognition & Analysis**

This document describes the security posture of the ASTRA project, the versions
we actively support, and how to responsibly disclose vulnerabilities.

---

## Supported Versions

Only the latest commit on the `main` branch is actively maintained. There are
no versioned releases at this time. Security fixes are applied directly to
`main` and are not backported.

| State | Coverage |
|---|---|
| `main` (latest) | Actively maintained — security fixes applied |
| Feature / fix branches | Not independently supported |
| Archived commits | No patches provided |

---

## Scope

The following components are in scope for security review:

### 1. Training and Data Pipeline (Python)

| Component | Path | Risk area |
|---|---|---|
| Data download manager | `pipeline/download_manager.py` | Untrusted catalog data, external HTTP requests |
| Preprocessing pipeline | `pipeline/preprocess.py` | Deserialization of `.npy` / `.npz` files |
| Dataset audit | `pipeline/dataset_audit.py` | Path traversal in audit filesystem operations |
| Phase 6 utilities | `pipeline/phase6_utils.py` | Hash verification bypass, CSV injection |
| Training loop | `training/train_cnn.py`, `training/train_transformer.py` | Unsafe `torch.load` without `weights_only` |
| Model export | `training/export_model.py` | Arbitrary code execution via TorchScript / ONNX |

### 2. Web Platform API (Next.js 16 — `astra-platform/`)

| Endpoint | Method | Risk area |
|---|---|---|
| `/api/stars` | GET | Query parameter injection, unbounded pagination |
| `/api/stars/[id]` | GET | Path traversal via dynamic segment |
| `/api/lightcurve/[id]` | GET | Filesystem path construction from user input, `.npy` deserialization |
| `/api/osint/[id]` | GET | SSRF via external cross-match requests |
| `/api/metrics` | GET | Exposure of internal checkpoint hashes and system paths |
| `/api/health` | GET | Disclosure of filesystem layout and checksum state |
| `/api/explain/[id]` | GET | ONNX model execution from user-controlled ID |
| `/api/upload` | POST | Arbitrary array input, detrending pipeline injection |

### Out of Scope

- Social engineering attacks against contributors
- Physical security of development hardware
- Third-party services (MAST, VSX, Gaia DR3, SIMBAD, ASAS-SN)
- Issues in dependencies that have been publicly disclosed and for which a
  patch is already available — please update the dependency instead

---

## Model Checkpoint Integrity

> **All `.pt` checkpoint files must be verified against their SHA-256 hashes
> before use in training, inference, or export.**

ASTRA stores checkpoint hashes in `models/saved/experiment_metadata.json`.
The file records a `checkpoint_sha256` field for every trained variant.

### Verification Procedure

```python
import hashlib, json
from pathlib import Path

def verify_checkpoint(checkpoint_path: str, variant: str) -> bool:
    """Return True if the checkpoint matches the recorded SHA-256 hash."""
    metadata_path = Path("models/saved/experiment_metadata.json")
    with open(metadata_path) as fh:
        metadata = json.load(fh)

    expected = metadata[variant]["checkpoint_sha256"]

    h = hashlib.sha256()
    with open(checkpoint_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()

    if actual != expected:
        raise RuntimeError(
            f"Checkpoint integrity failure for variant '{variant}'.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}\n"
            "Do not use this checkpoint."
        )
    return True
```

### Example — verifying the `dual_aug` checkpoint

```bash
python - <<'EOF'
import hashlib, json
from pathlib import Path

variant = "dual_aug"
checkpoint = Path("models/saved/best_star_cnn_dual_aug.pt")
metadata = json.loads(Path("models/saved/experiment_metadata.json").read_text())
expected = metadata[variant]["checkpoint_sha256"]

h = hashlib.sha256()
with open(checkpoint, "rb") as fh:
    for chunk in iter(lambda: fh.read(65536), b""):
        h.update(chunk)
actual = h.hexdigest()

status = "OK" if actual == expected else "FAIL — DO NOT USE"
print(f"[{status}] {checkpoint.name}")
print(f"  Expected: {expected}")
print(f"  Actual:   {actual}")
EOF
```

Known-good hashes recorded at training time (from `experiment_metadata.json`):

| Variant | Checkpoint file | SHA-256 (first 16 hex chars) |
|---|---|---|
| `dual_aug` | `best_star_cnn_dual_aug.pt` | `65da1034868c5460…` |
| `shared` | `best_star_transformer_shared.pt` | `bf374ce492825916…` |

> **Note:** The full 64-character hashes are the authoritative values.
> The table above shows truncated hashes for readability only. Always compare
> against the full hash in `experiment_metadata.json`.

### ONNX Exports

The ONNX exports (`best_star_transformer_shared.onnx`,
`best_star_transformer_shared_explain.onnx`) are served at runtime by the
`/api/explain/[id]` and `/api/upload` endpoints. Before deploying a new ONNX
export, verify it against the hash recorded in the corresponding
`experiment_metadata_*.json` file for that variant.

---

## Reporting a Vulnerability

**Do not open a public GitHub Issue for security vulnerabilities.**

We request private disclosure so that a fix can be prepared before the issue
becomes publicly known.

### How to Report

1. **Email:** Send a detailed report to the maintainer listed in the repository's
   contact information. Use the subject line:
   `[ASTRA SECURITY] <brief description>`.

2. **Content to include:**
   - A clear description of the vulnerability and the component(s) affected
   - Step-by-step reproduction instructions
   - The potential impact (e.g., arbitrary code execution, data exfiltration,
     model integrity bypass)
   - Any proof-of-concept code or payload (redact any real credentials)
   - Your preferred credit/attribution, if you would like to be acknowledged

3. **Encryption:** If your report contains especially sensitive information,
   request a PGP public key before sending.

---

## Response Timeline

| Milestone | Target |
|---|---|
| Acknowledgement of report | Within **48 hours** of receipt |
| Initial triage and severity assessment | Within **5 business days** |
| Fix developed and tested (for confirmed vulnerabilities) | Within **30 days** |
| Public disclosure (coordinated with reporter) | After fix is merged to `main` |

We follow a coordinated disclosure model. We ask reporters to hold off on public
disclosure until we have had a reasonable opportunity to investigate and release
a fix. We will keep you informed of our progress.

---

## Known Security Considerations

### `torch.load` and Pickle Deserialization

PyTorch checkpoint files (`.pt`) are Python pickle objects. Loading an untrusted
`.pt` file can execute arbitrary code. ASTRA mitigates this by:

- Only loading checkpoints from `models/saved/`, which is not user-writable
  in a deployed context
- Recording and checking SHA-256 hashes in `experiment_metadata.json` before
  loading any checkpoint
- Using `weights_only=True` where the PyTorch version supports it

Contributors must not add code that loads `.pt` files from user-supplied paths
without prior hash verification.

### NumPy `.npy` / `.npz` Deserialization

`numpy.load` with `allow_pickle=True` can execute arbitrary Python objects.
ASTRA's preprocessing pipeline uses `allow_pickle=False` for all array loads.
Do not introduce `allow_pickle=True` without explicit security review.

### API Rate Limiting and Authentication

The `astra-platform/` API endpoints currently serve read-only data from a local
filesystem database and do not implement authentication. The `POST /api/upload`
endpoint accepts arbitrary numeric arrays. Any deployment beyond localhost must
add:

- Authentication / API key validation before the upload endpoint
- Input size limits on the `flux` array
- Rate limiting on all endpoints

These are known gaps for a local-first research tool that become security
requirements upon public deployment.

---

## Acknowledgements

We thank all researchers and contributors who responsibly disclose security
issues. Your efforts help keep the scientific integrity and operational safety
of ASTRA intact.
