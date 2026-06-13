# ASTRA Phase 7A — Model Sanity Check Report

## 1. GPU Memory and Shape Audit

| Model | Batch Size | Output Shape | Inference Time (sec) | Peak MPS Memory (MB) |
| :--- | :---: | :---: | :---: | :---: |
| **CNN Dual** | 32 | (32, 5) | 0.2704 | 757.0 |
| **Transformer Shared** | 32 | (32, 5) | 0.2114 | 757.0 |
| **Transformer Cross** | 32 | (32, 5) | 0.0288 | 757.0 |
| **CNN Dual** | 64 | (64, 5) | 0.5851 | 1647.3 |
| **Transformer Shared** | 64 | (64, 5) | 0.2832 | 1647.3 |
| **Transformer Cross** | 64 | (64, 5) | 0.0704 | 1647.3 |

## 2. Verdict

✅ **All models instantiated successfully and forward passes are shape-aligned.**
