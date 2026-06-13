"""
ASTRA — Explainable Model Wrapper for ONNX Export.

Wraps the standard HybridTransformer model and returns intermediate representations
(attention weights, CNN features, pooled features) in its forward pass,
allowing full explainability export in ONNX.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from training.models.hybrid_transformer import HybridTransformer

class ExplainableHybridTransformerWrapper(nn.Module):
    """
    ONNX-compatible wrapper for HybridTransformer that exposes intermediate outputs
    required for attention-map and pipeline visualizers.
    """
    def __init__(self, base_model: HybridTransformer) -> None:
        super().__init__()
        self.base_model = base_model
        
    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if self.base_model.variant != "shared":
            raise ValueError("Explainable wrapper currently only supports the 'shared' variant.")
            
        raw = x[:, 0:1, :]       # (B, 1, 1000)
        folded = x[:, 1:2, :]    # (B, 1, 1000)

        # CNN Heads
        raw_head = self.base_model.raw_cnn_head(raw)       # (B, 128, 125)
        folded_head = self.base_model.folded_cnn_head(folded) # (B, 128, 125)
        
        # Concatenate CNN features along the temporal axis to form (B, 128, 250)
        cnn_features = torch.cat([raw_head, folded_head], dim=2)

        # CNN Tails (Baseline Features)
        raw_tail = self.base_model.raw_cnn_tail(raw_head).squeeze(-1)       # (B, 512)
        folded_tail = self.base_model.folded_cnn_tail(folded_head).squeeze(-1) # (B, 256)

        # Token transposes
        T_raw = raw_head.transpose(1, 2)       # (B, 125, 128)
        T_folded = folded_head.transpose(1, 2) # (B, 125, 128)

        # Add positional encodings
        T_raw = T_raw + self.base_model.pos_encoder
        T_folded = T_folded + self.base_model.pos_encoder

        # Add branch embeddings
        T_raw = T_raw + self.base_model.raw_branch_emb
        T_folded = T_folded + self.base_model.folded_branch_emb
        
        # Concatenate along sequence axis (B, 250, 128)
        T_joint = torch.cat([T_raw, T_folded], dim=1)
        
        attn_w = torch.zeros(x.shape[0], 250, 250, device=x.device)
        for layer in self.base_model.shared_transformer:
            T_joint, attn_w = layer(T_joint)
            
        pooled_features = T_joint.mean(dim=1) # (B, 128)
        combined = torch.cat([pooled_features, raw_tail, folded_tail], dim=1) # (B, 896)
        logits = self.base_model.classifier(combined)
        
        return logits, attn_w, cnn_features, pooled_features
