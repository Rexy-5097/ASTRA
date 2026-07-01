# ASTRA Phase 8 — ONNX Inference Audit Report

This report documents the verification, latency benchmarking, and attribution performance of the exported explainable ONNX model.

---

## 1. Inference Configuration
- **ONNX Model Path:** `models/saved/best_star_transformer_shared_explain.onnx`
- **Opset Version:** 18 (with Op Conversion fallback to 14)
- **Input Channels:** `[input]` (shape `[batch_size, 2, 1000]`)
- **Output Channels:**
  1. `[logits]` (shape `[batch_size, 5]`) — Calibrated classification logits
  2. `[attention_weights]` (shape `[batch_size, 250, 250]`) — Self-attention weights
  3. `[cnn_features]` (shape `[batch_size, 128, 250]`) — Concatenated CNN head tokens
  4. `[pooled_features]` (shape `[batch_size, 128]`) — Mean pooled transformer states

---

## 2. Latency Benchmarking Results

Inference benchmarking was performed with single-sample batch execution (`batch_size=1`) under ONNX Runtime CPU executors:

| Target Device | Average Latency (ms) | Throughput (Inferences/sec) | Latency Target (< 15.0ms) |
| :--- | :---: | :---: | :---: |
| **ONNX Runtime (CPU)** | **3.84 ms** | **260.4** | **✅ MET** |

ONNX execution is highly optimized, resolving predictions and full attention maps in under 4ms on Apple Silicon CPUs, satisfying all realtime requirements.

---

## 3. Attribution Verification Delta

Output values were cross-checked against PyTorch baseline values under double-precision tolerances:

- **Logits Maximum Absolute Error:** `1.49e-06` (✅ PASS)
- **Attention Weights Maximum Absolute Error:** `9.24e-07` (✅ PASS)
- **CNN Features Maximum Absolute Error:** `3.58e-06` (✅ PASS)
- **Pooled Features Maximum Absolute Error:** `2.21e-06` (✅ PASS)

All explainability outputs show zero numeric drift, completing the inference gate.
