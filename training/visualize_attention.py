"""
ASTRA — Attention Visualization and Phase-Region Attribution Mapping.

This script loads a trained HybridTransformer model checkpoint, selects representative
validation stars of each class (RR Lyrae, Cepheid, Eclipsing Binary, Solar-Like, Stable),
runs a forward pass to extract the attention weights, and generates:
  1. 2D attention weight heatmaps.
  2. 1D light curve overlays showing attention weight magnitudes plotted on top of the flux.

Outputs are saved directly to the specified artifacts directory.
"""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from data.labels import CLASS_NAMES, LABEL_TO_NAME, NUM_CLASSES
from training.dataset import ASTRADataset
from training.models.hybrid_transformer import HybridTransformer


def get_representative_stars(dataset: ASTRADataset) -> dict[int, int]:
    """Find the index of one representative star for each of the 5 classes in the dataset."""
    found = {}
    for idx, sample in enumerate(dataset._samples):
        label = sample["label"]
        if label not in found:
            # Let's verify we can load it successfully
            try:
                dataset[idx]
                found[label] = idx
            except Exception:
                continue
        if len(found) == NUM_CLASSES:
            break
    return found


def plot_attention_1d(
    flux_1d: np.ndarray,
    attn_1d: np.ndarray,
    title: str,
    xlabel: str,
    save_path: Path,
    color_flux: str = "royalblue",
    color_attn: str = "crimson",
) -> None:
    """Plot 1D light curve with attention weights overlaid as a shaded background."""
    fig, ax1 = plt.subplots(figsize=(10, 4))

    # Plot light curve
    ax1.plot(flux_1d, color=color_flux, alpha=0.8, linewidth=1.5, label="Normalized Flux")
    ax1.set_xlabel(xlabel, fontsize=12)
    ax1.set_ylabel("Flux (Normalized)", color=color_flux, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color_flux)
    ax1.grid(True, alpha=0.2)

    # Plot attention overlay
    ax2 = ax1.twinx()
    x = np.arange(len(flux_1d))
    ax2.fill_between(x, attn_1d, color=color_attn, alpha=0.3, label="Attention Weight")
    ax2.plot(x, attn_1d, color=color_attn, alpha=0.8, linewidth=1.0)
    ax2.set_ylabel("Attention Weight (Normalized)", color=color_attn, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=color_attn)
    ax2.set_ylim(0, max(attn_1d) * 1.1 if max(attn_1d) > 0 else 1.0)

    plt.title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Attention Weight Visualization")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to trained .pt checkpoint")
    parser.add_argument("--output-dir", type=str, required=True, help="Artifact output directory")
    parser.add_argument("--data-dir", type=str, default="data/processed")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = Path(args.checkpoint)

    # ── Load Checkpoint ──
    print(f"Loading checkpoint: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    variant = ckpt["variant"]
    use_folded = ckpt["use_folded"]

    # ── Instantiate Model ──
    model = HybridTransformer(variant=variant, num_classes=NUM_CLASSES)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    # ── Load Dataset ──
    dataset = ASTRADataset(data_dir=args.data_dir, split="val", use_folded=use_folded, augment=False)
    rep_stars = get_representative_stars(dataset)

    print(f"Generating attention plots for variant: '{variant}'...")

    for label, idx in rep_stars.items():
        class_name = LABEL_TO_NAME[label]
        sample = dataset._samples[idx]
        tic_id = sample["tic_id"]
        
        # Load raw data for plotting
        raw_flux = np.load(sample["flux_path"]).astype(np.float32)
        folded_flux = np.load(sample["folded_flux_path"]).astype(np.float32) if use_folded else None

        # Run forward pass
        flux_tensor, _ = dataset[idx]
        with torch.no_grad():
            _ = model(flux_tensor.unsqueeze(0))
        
        # Extract attention weights
        # Shape: (1, L_q, L_k)
        attn_w = model.last_attention_weights
        if attn_w is None:
            print(f"  ⚠ Attention weights missing for {class_name}. Skipping.")
            continue
        attn_matrix = attn_w[0].numpy()  # (L_q, L_k)

        # ── 1. Save 2D Heatmap ──
        fig, ax = plt.subplots(figsize=(8, 7))
        sns.heatmap(
            attn_matrix,
            cmap="viridis",
            cbar=True,
            ax=ax,
            square=True,
        )
        ax.set_title(f"2D Attention Matrix: {class_name} ({tic_id})", fontsize=12, fontweight="bold")
        
        if variant == "cross":
            ax.set_xlabel("Keys (Raw Time Tokens, 0..124)", fontsize=10)
            ax.set_ylabel("Queries (Folded Phase Tokens, 0..124)", fontsize=10)
        elif variant == "shared":
            ax.set_xlabel("Keys (Raw 0..124, Folded 125..249)", fontsize=10)
            ax.set_ylabel("Queries (Raw 0..124, Folded 125..249)", fontsize=10)
        else:
            ax.set_xlabel("Keys (Tokens, 0..124)", fontsize=10)
            ax.set_ylabel("Queries (Tokens, 0..124)", fontsize=10)

        plt.tight_layout()
        heatmap_path = output_dir / f"attn_heatmap_{variant}_{class_name}.png"
        plt.savefig(heatmap_path, dpi=150)
        plt.close()
        print(f"  Saved 2D Heatmap → {heatmap_path.name}")

        # ── 2. Interpolate and Save 1D Attribution Overlays ──
        # Compute 1D importance vectors by averaging attention
        if variant == "only" or variant == "separate":
            # For self-attention, average queries to get key-importance
            attn_1d = attn_matrix.mean(axis=0)  # (125,)
            # Interpolate to 1000 points to match flux
            attn_1000 = np.interp(np.linspace(0, 124, 1000), np.arange(125), attn_1d)
            # Normalize to [0, 1] for visualization
            if attn_1000.max() > 0:
                attn_1000 = attn_1000 / attn_1000.max()

            plot_attention_1d(
                flux_1d=raw_flux,
                attn_1d=attn_1000,
                title=f"Raw Flux & Self-Attention: {class_name} ({tic_id})",
                xlabel="Time Step (Raw)",
                save_path=output_dir / f"attn_overlay_raw_{variant}_{class_name}.png",
            )
            print(f"  Saved 1D Raw Overlay → attn_overlay_raw_{variant}_{class_name}.png")

        elif variant == "shared":
            # Joint attention (250, 250). Splitting into raw (0..124) and folded (125..249)
            # Raw importance: average attention weights received by raw keys (cols 0..124)
            attn_raw_1d = attn_matrix[:, :125].mean(axis=0)  # (125,)
            attn_raw_1000 = np.interp(np.linspace(0, 124, 1000), np.arange(125), attn_raw_1d)
            if attn_raw_1000.max() > 0:
                attn_raw_1000 = attn_raw_1000 / attn_raw_1000.max()

            # Folded importance: average attention weights received by folded keys (cols 125..249)
            attn_fold_1d = attn_matrix[:, 125:].mean(axis=0)  # (125,)
            attn_fold_1000 = np.interp(np.linspace(0, 124, 1000), np.arange(125), attn_fold_1d)
            if attn_fold_1000.max() > 0:
                attn_fold_1000 = attn_fold_1000 / attn_fold_1000.max()

            plot_attention_1d(
                flux_1d=raw_flux,
                attn_1d=attn_raw_1000,
                title=f"Raw Flux & Shared Self-Attention: {class_name} ({tic_id})",
                xlabel="Time Step (Raw)",
                save_path=output_dir / f"attn_overlay_raw_{variant}_{class_name}.png",
                color_attn="crimson",
            )
            plot_attention_1d(
                flux_1d=folded_flux,
                attn_1d=attn_fold_1000,
                title=f"Folded Flux & Shared Self-Attention: {class_name} ({tic_id})",
                xlabel="Phase Step (Folded)",
                save_path=output_dir / f"attn_overlay_folded_{variant}_{class_name}.png",
                color_flux="seagreen",
                color_attn="purple",
            )
            print(f"  Saved 1D Raw/Folded Overlays → attn_overlay_*_{variant}_{class_name}.png")

        elif variant == "cross":
            # Queries = Folded (phase), Keys = Raw (time)
            # Shape is (125, 125). Columns are raw time keys, rows are folded phase queries.
            # 1. Raw time importance: average over phase queries (mean along axis=0)
            attn_raw_1d = attn_matrix.mean(axis=0)  # (125,)
            attn_raw_1000 = np.interp(np.linspace(0, 124, 1000), np.arange(125), attn_raw_1d)
            if attn_raw_1000.max() > 0:
                attn_raw_1000 = attn_raw_1000 / attn_raw_1000.max()

            # 2. Folded phase importance: average over raw keys (mean along axis=1)
            attn_fold_1d = attn_matrix.mean(axis=1)  # (125,)
            attn_fold_1000 = np.interp(np.linspace(0, 124, 1000), np.arange(125), attn_fold_1d)
            if attn_fold_1000.max() > 0:
                attn_fold_1000 = attn_fold_1000 / attn_fold_1000.max()

            plot_attention_1d(
                flux_1d=raw_flux,
                attn_1d=attn_raw_1000,
                title=f"Raw Flux & Cross-Attention: {class_name} ({tic_id})",
                xlabel="Time Step (Raw)",
                save_path=output_dir / f"attn_overlay_raw_{variant}_{class_name}.png",
                color_attn="crimson",
            )
            plot_attention_1d(
                flux_1d=folded_flux,
                attn_1d=attn_fold_1000,
                title=f"Folded Flux & Cross-Attention: {class_name} ({tic_id})",
                xlabel="Phase Step (Folded)",
                save_path=output_dir / f"attn_overlay_folded_{variant}_{class_name}.png",
                color_flux="seagreen",
                color_attn="purple",
            )
            print(f"  Saved 1D Raw/Folded Overlays → attn_overlay_*_{variant}_{class_name}.png")

    print("\n✅ Attention visualization generation complete!")


if __name__ == "__main__":
    main()
