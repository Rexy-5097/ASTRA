# ASTRA Phase 7C — Ground Truth Attention Weights Audit

This report verifies the structural attributes, dimensionality, entropy, and sparsity of self-attention maps in the Transformer Shared encoder model.

## 1. Attention Weights Properties

- **Attention Tensors Shape (N, L_seq, L_seq)**: `(142, 250, 250)`
- **Mean query-wise Shannon entropy**: `3.1618`
- **Mean attention sparsity (fraction of elements < 0.01)**: `93.33%`
