# ASTRA Phase 8 — API Audit Report

This report documents the verification, routing, and schema structures for all active REST API endpoints serving the ASTRA Stellar Intelligence Platform.

---

## 1. API Endpoints Registry

The Next.js App Router exposes 8 serverless endpoints providing real data from filesystem arrays and the SQLite database:

### A. Core Star Registries
1. **`GET /api/stars`**
   - **Purpose:** Searches the 944-star database with optional paging and filtering.
   - **Parameters:** `q` (text search), `class` (rr_lyrae, cepheid, eclipsing_binary, solar_like, stable), `source` (catalog, BLS), `split` (train, val, test), `page`, `limit`.
   - **Output:** Paginated list of star details.
2. **`GET /api/stars/[id]`**
   - **Purpose:** Retrieves a single star's coordinate metadata, parameters, and observations.
   - **Output:** Detailed star JSON block.

### B. Time-Series & Cross-Match Intelligence
3. **`GET /api/lightcurve/[id]`**
   - **Purpose:** Locates target `.npy` arrays, decodes floats, and generates 1000-point raw and 200-point folded curves.
   - **Output:** `{ tic_id, flux_1000: [...], folded_flux_200: [...] }`
4. **`GET /api/osint/[id]`**
   - **Purpose:** Synthesizes Gaia DR3 coordinates, SIMBAD variable classifications, and ASAS-SN observation epochs.
   - **Output:** Detailed Space OSINT target dossier.

### C. MLOps, Health, & Explainability
5. **`GET /api/metrics`**
   - **Purpose:** Serves recomputed model parameters, temperature scalings, ECE histograms, and checkpoint registry hashes.
   - **Output:** Global performance metrics.
6. **`GET /api/health`**
   - **Purpose:** Runs dynamic filesystem and checksum checks, reporting system status (`READY`, `DEGRADED`, `BLOCKED`).
   - **Output:** Live system health indicators.
7. **`GET /api/explain/[id]`**
   - **Purpose:** Executes explainable ONNX model inference, returning logits, attention weights `[250, 250]`, and CNN features.
   - **Output:** Model interpretability reports.
8. **`POST /api/upload`**
   - **Purpose:** Receives custom raw photometry arrays, performs detrending and linear folding, and runs ONNX explainability checks.
   - **Input:** `{ tic_id, period, flux: [number[] or csv string] }`
   - **Output:** Custom target prediction and attention weights mapping.

---

## 2. Dynamic Integration Check
All 8 endpoints have been verified using end-to-end `curl` testing, returning `200 OK` responses with zero runtime exceptions.
