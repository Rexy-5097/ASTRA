# ASTRA Web Platform API Reference

> **Note**: All API endpoints serve data from verified artifacts and processed datasets.
> No data is generated at request time — all responses reflect pre-computed, audited results.

---

## Base URL

```
http://localhost:3000/api  (development)
```

---

## Endpoints

### `GET /api/health`

System health check. Returns status of data availability and model checkpoint integrity.

**Response:**
```json
{
  "status": "ok",
  "dataset_stars": 944,
  "checkpoints": {
    "transformer_shared": "present",
    "cnn_dual": "present"
  },
  "timestamp": "2026-06-13T00:00:00Z"
}
```

---

### `GET /api/stars`

Returns the full star catalog.

**Query parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `class` | string | Filter by class name (e.g., `rr_lyrae`, `cepheid`) |
| `limit` | number | Max results (default: 50) |
| `offset` | number | Pagination offset |

**Response:**
```json
{
  "total": 944,
  "stars": [
    {
      "tic_id": "261136679",
      "class": "rr_lyrae",
      "label": 0
    }
  ]
}
```

---

### `GET /api/stars/:id`

Returns metadata for a single star.

**Parameters:** TIC ID as path parameter

**Response:**
```json
{
  "tic_id": "261136679",
  "class": "rr_lyrae",
  "label": 0,
  "metadata": { ... }
}
```

---

### `GET /api/lightcurve/:id`

Returns the preprocessed light curve arrays for visualization.

**Response:**
```json
{
  "tic_id": "...",
  "flux_1000": [0.001, -0.002, ...],
  "flux_200": [0.01, 0.02, ...]
}
```

---

### `GET /api/predict/:id`

Returns model predictions for a star.

**Response:**
```json
{
  "tic_id": "...",
  "predictions": {
    "class": "rr_lyrae",
    "label": 0,
    "probabilities": {
      "rr_lyrae": 0.87,
      "cepheid": 0.05,
      "eclipsing_binary": 0.03,
      "solar_like": 0.03,
      "stable": 0.02
    },
    "confidence": 0.87,
    "entropy": 0.12
  }
}
```

---

### `GET /api/explain/:id`

Returns attention weights for explainability visualization.

**Response:**
```json
{
  "tic_id": "...",
  "attention_weights": [[...], [...]],
  "class": "rr_lyrae"
}
```

---

### `GET /api/metrics`

Returns aggregate model performance metrics from verified benchmark.

**Response:**
```json
{
  "transformer_shared": {
    "test_accuracy": 0.7817,
    "macro_f1": 0.7677,
    "weighted_f1": 0.7784,
    "ci_accuracy": [0.7113, 0.8521],
    "ci_macro_f1": [0.6944, 0.8320]
  },
  "cnn_dual": {
    "test_accuracy": 0.7817,
    "macro_f1": 0.7635,
    "weighted_f1": 0.7756,
    "ci_accuracy": [0.7183, 0.8451],
    "ci_macro_f1": [0.6923, 0.8301]
  }
}
```

---

### `GET /api/dataset`

Returns dataset summary statistics.

**Response:**
```json
{
  "version": "2.0",
  "total_stars": 944,
  "fingerprint_hash": "f99b4b06...",
  "freeze_date": "2026-06-12",
  "class_distribution": {
    "rr_lyrae": { "count": 220, "label": 0 },
    "cepheid": { "count": 180, "label": 1 },
    "eclipsing_binary": { "count": 200, "label": 2 },
    "solar_like": { "count": 160, "label": 3 },
    "stable": { "count": 184, "label": 4 }
  }
}
```

---

### `GET /api/benchmark`

Returns full benchmark comparison table.

---

### `GET /api/calibration`

Returns temperature calibration parameters and reliability metrics.

---

### `GET /api/checkpoints`

Returns model checkpoint registry with SHA256 hashes.

---

### `GET /api/model`

Returns model architecture summary (parameter counts, variant details).

---

### `GET /api/search`

Full-text search across star catalog.

**Query parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (TIC ID, class name) |

---

### `GET /api/research`

Returns research context and related literature links.

---

### `GET /api/osint/:id`

Returns external catalog cross-references for a star (VSX, SIMBAD links).

---

### `POST /api/upload`

Upload a custom `.npy` flux array for inference.

**Body:** `multipart/form-data` with `flux` field (1000-point float32 array)

**Response:** Same as `/api/predict/:id`

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Star not found |
| 422 | Invalid input |
| 500 | Internal server error |

Error response format:
```json
{
  "error": "Star TIC_999999 not found in processed dataset"
}
```
