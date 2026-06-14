"""
ASTRA — Hybrid CNN + Transformer Model for Variable Star Classification.

This module implements a publishable-quality hybrid CNN + Transformer classifier
equipped with self-attention and cross-attention variants, custom return-attention
layers for attribution mapping, and full MPS acceleration support on macOS.

Supported Variants:
    1. 'separate': Separate self-attention encoders for raw and folded branches.
    2. 'shared'  : Shared self-attention encoder processing joint raw+folded tokens.
    3. 'cross'   : Cross-attention encoder where folded tokens query raw tokens.
    4. 'only'    : Transformer-only baseline with linear patch embeddings.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn

from data.labels import NUM_CLASSES


class TransformerEncoderLayerCustom(nn.Module):
    """
    Custom Pre-LN Transformer Encoder Layer that returns attention weights
    for scientific interpretability and visualization.
    """
    def __init__(self, d_model: int = 128, nhead: int = 4, dim_feedforward: int = 256, dropout: float = 0.2) -> None:
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(dim_feedforward, d_model)

        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # Pre-LN Self-Attention
        x2 = self.norm1(x)
        attn_out, attn_weights = self.self_attn(x2, x2, x2)
        x = x + self.dropout1(attn_out)

        # Pre-LN Feed-Forward Network
        x2 = self.norm2(x)
        ff_out = self.linear2(self.dropout(torch.relu(self.linear1(x2))))
        x = x + self.dropout2(ff_out)

        return x, attn_weights


class HybridTransformer(nn.Module):
    """
    Hybrid CNN + Transformer classifier for variable star classification.
    """
    def __init__(
        self,
        num_classes: int = NUM_CLASSES,
        variant: str = "shared",
        embed_dim: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.variant = variant
        self.embed_dim = embed_dim

        # Validate variant
        valid_variants = ["separate", "shared", "cross", "only", "shared_no_folded", "shared_no_folded_matched"]
        if variant not in valid_variants:
            raise ValueError(f"Unknown variant '{variant}'. Choose from {valid_variants}")

        # Learnable positional encodings
        # Sequence length L=125 after 3 blocks of pooling (1000 -> 500 -> 250 -> 125)
        self.pos_encoder = nn.Parameter(torch.randn(1, 125, embed_dim) * 0.02)
        self.last_attention_weights = None

        if variant == "only":
            # Transformer-only mode: Linear projection of 8-point patches
            self.patch_proj = nn.Conv1d(1, embed_dim, kernel_size=8, stride=8)
            encoder_layers = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            self.transformer_layers = nn.ModuleList(encoder_layers)

            # Simple classifier for single branch
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(embed_dim, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(256, num_classes)
            )
            return

        # ── CNN Feature Tokenizers (Common to separate, shared, cross) ─────────
        # Processes raw & folded inputs into sequence tokens of shape (B, 128, 125)
        self.raw_cnn_head = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(64, embed_dim, kernel_size=5, padding=2),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
        )

        self.folded_cnn_head = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(64, embed_dim, kernel_size=5, padding=2),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
        )

        # CNN tail branches for baseline feature representation
        self.raw_cnn_tail = nn.Sequential(
            nn.Conv1d(embed_dim, 256, kernel_size=3, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )

        self.folded_cnn_tail = nn.Sequential(
            nn.Conv1d(embed_dim, 256, kernel_size=3, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.AdaptiveAvgPool1d(1),
        )

        # ── Attention Layers depending on Variant ──────────────────────────────
        if variant == "separate":
            raw_encoder = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            folded_encoder = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            self.raw_transformer = nn.ModuleList(raw_encoder)
            self.folded_transformer = nn.ModuleList(folded_encoder)

            # Classifier: 128 (raw attn) + 128 (folded attn) + 512 (raw CNN) + 256 (folded CNN) = 1024
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(1024, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(384, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(128, num_classes)
            )

        elif variant == "shared":
            shared_encoder = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            self.shared_transformer = nn.ModuleList(shared_encoder)
            self.raw_branch_emb = nn.Parameter(torch.randn(1, 1, embed_dim) * 0.02)
            self.folded_branch_emb = nn.Parameter(torch.randn(1, 1, embed_dim) * 0.02)

            # Classifier: 128 (joint attention) + 512 (raw CNN) + 256 (folded CNN) = 896
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(896, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(384, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(128, num_classes)
            )

        elif variant == "shared_no_folded":
            shared_encoder = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            self.shared_transformer = nn.ModuleList(shared_encoder)

            # Classifier: 128 (raw attention) + 512 (raw CNN) = 640
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(640, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(384, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(128, num_classes)
            )

        elif variant == "shared_no_folded_matched":
            shared_encoder = [TransformerEncoderLayerCustom(embed_dim, nhead, embed_dim * 2, dropout) for _ in range(num_layers)]
            self.shared_transformer = nn.ModuleList(shared_encoder)

            # Projection head: 128 -> 384 -> 256
            self.proj_head = nn.Sequential(
                nn.Linear(embed_dim, 384),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(384, 256),
                nn.Dropout(dropout),
            )

            # Classifier: 256 (projected attention) + 512 (raw CNN) = 768
            # Dimensions adjusted so the parameter count matches the shared variant (~1.37M params)
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(768, 225),
                nn.BatchNorm1d(225),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(225, 105),
                nn.BatchNorm1d(105),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(105, num_classes)
            )

        elif variant == "cross":
            # Multi-head cross attention: Folded tokens query Raw tokens
            self.cross_attn = nn.MultiheadAttention(embed_dim, nhead, dropout=dropout, batch_first=True)
            self.cross_norm1 = nn.LayerNorm(embed_dim)
            self.cross_norm2 = nn.LayerNorm(embed_dim)
            self.cross_ffn = nn.Sequential(
                nn.Linear(embed_dim, embed_dim * 2),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(embed_dim * 2, embed_dim),
                nn.Dropout(dropout),
            )

            # Classifier: 128 (cross attention) + 512 (raw CNN) + 256 (folded CNN) = 896
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(896, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(384, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(128, num_classes)
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.variant == "only":
            raw = x[:, 0:1, :] # (B, 1, 1000)
            tokens = self.patch_proj(raw).transpose(1, 2) # (B, 125, 128)
            tokens = tokens + self.pos_encoder

            attn_w = None
            for layer in self.transformer_layers:
                tokens, attn_w = layer(tokens)
            if not torch.onnx.is_in_onnx_export():
                self.last_attention_weights = attn_w.detach().cpu()

            pooled = tokens.mean(dim=1)
            return self.classifier(pooled)

        # ── Raw-Only Shared Variants ──
        if self.variant in ("shared_no_folded", "shared_no_folded_matched"):
            raw = x[:, 0:1, :] # (B, 1, 1000)
            raw_head = self.raw_cnn_head(raw) # (B, 128, 125)
            raw_tail = self.raw_cnn_tail(raw_head).squeeze(-1) # (B, 512)

            T_raw = raw_head.transpose(1, 2) # (B, 125, 128)
            T_raw = T_raw + self.pos_encoder

            attn_w = None
            for layer in self.shared_transformer:
                T_raw, attn_w = layer(T_raw)
            if not torch.onnx.is_in_onnx_export():
                self.last_attention_weights = attn_w.detach().cpu()

            pooled = T_raw.mean(dim=1) # (B, 128)

            if self.variant == "shared_no_folded":
                combined = torch.cat([pooled, raw_tail], dim=1) # (B, 640)
            else: # shared_no_folded_matched
                projected = self.proj_head(pooled) # (B, 256)
                combined = torch.cat([projected, raw_tail], dim=1) # (B, 768)

            return self.classifier(combined)

        # ── Dual Branch Input ──
        raw = x[:, 0:1, :]       # (B, 1, 1000)
        folded = x[:, 1:2, :]    # (B, 1, 1000)

        # CNN Heads
        raw_head = self.raw_cnn_head(raw)       # (B, 128, 125)
        folded_head = self.folded_cnn_head(folded) # (B, 128, 125)

        # CNN Tails (Baseline Features)
        raw_tail = self.raw_cnn_tail(raw_head).squeeze(-1)       # (B, 512)
        folded_tail = self.folded_cnn_tail(folded_head).squeeze(-1) # (B, 256)

        # Token transposes
        T_raw = raw_head.transpose(1, 2)       # (B, 125, 128)
        T_folded = folded_head.transpose(1, 2) # (B, 125, 128)

        # Add positional encodings
        T_raw = T_raw + self.pos_encoder
        T_folded = T_folded + self.pos_encoder

        if self.variant == "separate":
            attn_w_raw, attn_w_fold = None, None
            for layer in self.raw_transformer:
                T_raw, attn_w_raw = layer(T_raw)
            for layer in self.folded_transformer:
                T_folded, attn_w_fold = layer(T_folded)

            # Save raw attention map for visualization
            if not torch.onnx.is_in_onnx_export():
                self.last_attention_weights = attn_w_raw.detach().cpu()

            pooled_raw = T_raw.mean(dim=1)     # (B, 128)
            pooled_folded = T_folded.mean(dim=1) # (B, 128)

            combined = torch.cat([pooled_raw, pooled_folded, raw_tail, folded_tail], dim=1) # (B, 1024)

        elif self.variant == "shared":
            # Add branch embeddings
            T_raw = T_raw + self.raw_branch_emb
            T_folded = T_folded + self.folded_branch_emb

            # Concatenate along sequence axis (B, 250, 128)
            T_joint = torch.cat([T_raw, T_folded], dim=1)

            attn_w = None
            for layer in self.shared_transformer:
                T_joint, attn_w = layer(T_joint)

            if not torch.onnx.is_in_onnx_export():
                self.last_attention_weights = attn_w.detach().cpu()

            pooled_joint = T_joint.mean(dim=1) # (B, 128)
            combined = torch.cat([pooled_joint, raw_tail, folded_tail], dim=1) # (B, 896)

        elif self.variant == "cross":
            # Queries = Folded, Keys/Values = Raw
            T_folded_norm = self.cross_norm1(T_folded)
            attn_out, attn_weights = self.cross_attn(
                query=T_folded_norm,
                key=T_raw,
                value=T_raw,
            )
            T_cross = T_folded + attn_out

            # FFN block
            T_cross_norm = self.cross_norm2(T_cross)
            T_cross = T_cross + self.cross_ffn(T_cross_norm)

            if not torch.onnx.is_in_onnx_export():
                self.last_attention_weights = attn_weights.detach().cpu()
            pooled_cross = T_cross.mean(dim=1) # (B, 128)
            combined = torch.cat([pooled_cross, raw_tail, folded_tail], dim=1) # (B, 896)

        return self.classifier(combined)

    @staticmethod
    def count_parameters(model: nn.Module) -> dict[str, int]:
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return {"total": total, "trainable": trainable}


if __name__ == "__main__":
    print("=" * 70)
    print("  HybridTransformer — Architecture Verification")
    print("=" * 70)

    dummy_input = torch.randn(2, 2, 1000)
    dummy_input_only = torch.randn(2, 1, 1000)

    for var in ["separate", "shared", "cross", "only", "shared_no_folded", "shared_no_folded_matched"]:
        print(f"\n[Variant: '{var}']")
        if var == "only":
            model = HybridTransformer(variant=var)
            inp = dummy_input_only
        else:
            model = HybridTransformer(variant=var)
            inp = dummy_input

        params = HybridTransformer.count_parameters(model)
        print(f"  Total parameters:     {params['total']:,}")
        print(f"  Trainable parameters: {params['trainable']:,}")

        with torch.no_grad():
            out = model(inp)
        print(f"  Input shape:          {tuple(inp.shape)}")
        print(f"  Output shape:         {tuple(out.shape)}")
        print(f"  Attention map shape:  {tuple(model.last_attention_weights.shape)}")

        assert out.shape == (2, NUM_CLASSES)
        assert params["total"] < 3_000_000, "Parameter count exceeds 3M limit!"
        print(f"  ✅ Verification passed for variant '{var}'")
