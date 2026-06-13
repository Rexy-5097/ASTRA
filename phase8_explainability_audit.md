# ASTRA Phase 8A — Explainability Export Validation Report

This report documents the successful verification of the multi-output **Explainability ONNX Export Gate** under Phase 8A.

## 1. Verification Details
- **Timestamp:** 2026-06-13T02:20:30Z
- **Source Checkpoint:** `best_star_transformer_shared.pt`
- **Model Checkpoint SHA256:** bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388
- **Exported ONNX File:** `best_star_transformer_shared_explain.onnx`
- **Target Ops:** ONNX Opset 14

## 2. Dynamic Shape & Attribution Verification

The model is successfully exported with multiple explainability channels, yielding identical numerical results to the native PyTorch implementation:

| Output Channel | Expected PyTorch Shape | ONNX Runtime Shape | Max Output Difference | Validation Status |
| :--- | :---: | :---: | :---: | :---: |
| **logits** | `[batch_size, 5]` | `[batch_size, 5]` | `1.49e-06` | ✅ PASS |
| **attention_weights** | `[batch_size, 250, 250]` | `[batch_size, 250, 250]` | `9.24e-07` | ✅ PASS |
| **cnn_features** | `[batch_size, 128, 250]` | `[batch_size, 128, 250]` | `3.58e-06` | ✅ PASS |
| **pooled_features** | `[batch_size, 128]` | `[batch_size, 128]` | `2.21e-06` | ✅ PASS |

## 3. Inference Latency
- **ONNX CPU Average Latency:** 4.83 ms (single sample batch, dynamic batch size active)

## 4. Pipeline Integration
The `/api/explain` and `/api/mission-replay` runtimes can now safely rely on the exported `best_star_transformer_shared_explain.onnx` file to extract raw convolutional feature maps, self-attention maps, and pooled activations directly without invoking active PyTorch runtimes, completing the Explainability Gate.
