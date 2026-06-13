"""
ASTRA — Training script for Hybrid CNN + Transformer variable star classifier.

Supports training the 6 variants: 'separate', 'shared', 'cross', 'only',
'shared_no_folded', 'shared_no_folded_matched' on Apple Silicon MPS (GPU) with
strict determinism, checkpoint hashing, and environment metadata tracking.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import math
import random
import hashlib
import subprocess
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data.labels import CLASS_NAMES, LABEL_TO_NAME, NUM_CLASSES
from pipeline.phase6_utils import assert_phase6_training_allowed
from training.dataset import ASTRADataset
from training.focal_loss import FocalLoss
from training.models.hybrid_transformer import HybridTransformer

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)


# ─── Seeding and Determinism ─────────────────────────────────────────
def set_deterministic_seeds(seed: int = 42) -> None:
    """Enforce strict seed-based determinism across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        
    try:
        # Enforce deterministic algorithms if supported
        torch.use_deterministic_algorithms(True)
        logger.info("Strict PyTorch deterministic algorithms enabled.")
    except Exception as e:
        logger.warning(
            f"PyTorch strict deterministic algorithms could not be enabled (due to MPS limitations). "
            f"Falling back to seed-based determinism. Exception: {e}"
        )


# ─── Checkpoint File Hashing ──────────────────────────────────────────
def get_file_sha256(path: Path) -> str:
    """Compute the SHA256 checksum of a file for experiment reproducibility audits."""
    if not path.exists():
        return "file_not_found"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


# ─── Device Selection ────────────────────────────────────────────────
def get_device() -> torch.device:
    """Select MPS if available, otherwise CPU. Never CUDA."""
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        logger.info("Using device: MPS (Apple Silicon GPU)")
    else:
        device = torch.device("cpu")
        logger.info("Using device: CPU")
    return device


# ─── GPU Memory Tracking ─────────────────────────────────────────────
def get_gpu_memory_mb() -> float:
    """Return current allocated MPS memory in MB. Return 0.0 if not on MPS."""
    if torch.backends.mps.is_available():
        try:
            return torch.mps.current_allocated_memory() / (1024 * 1024)
        except Exception:
            return 0.0
    return 0.0


# ─── Attention Entropy ───────────────────────────────────────────────
def compute_attention_entropy(attn_weights: torch.Tensor) -> float:
    """Compute mean Shannon entropy (in nats) of the attention probability distribution.
    
    attn_weights shape: (B, L, L) or similar.
    Entropy is computed along the last dimension (keys).
    """
    if attn_weights is None:
        return 0.0
    eps = 1e-9
    # Shannon entropy: H = -sum(p * log(p + eps))
    entropy = -torch.sum(attn_weights * torch.log(attn_weights + eps), dim=-1)
    return entropy.mean().item()


# ─── Focal Loss with Label Smoothing ─────────────────────────────────
class RegularizedFocalLoss(nn.Module):
    """
    Focal Loss with support for label smoothing.
    """
    def __init__(self, alpha: torch.Tensor | None = None, gamma: float = 2.0, label_smoothing: float = 0.1) -> None:
        super().__init__()
        self.gamma = gamma
        self.label_smoothing = label_smoothing
        if alpha is not None:
            self.register_buffer("alpha", alpha)
        else:
            self.alpha = None

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Cross entropy with label smoothing
        log_probs = torch.log_softmax(inputs, dim=-1)
        
        # Build soft targets
        num_classes = inputs.size(-1)
        with torch.no_grad():
            targets_smooth = torch.empty_like(inputs).fill_(self.label_smoothing / (num_classes - 1))
            targets_smooth.scatter_(1, targets.unsqueeze(1), 1.0 - self.label_smoothing)
            
        ce_loss = -torch.sum(targets_smooth * log_probs, dim=-1)
        
        # Focal modulation factor
        # Probabilities p_t corresponding to the true classes
        probs = torch.softmax(inputs, dim=-1)
        p_t = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        focal_weight = (1.0 - p_t) ** self.gamma
        
        loss = focal_weight * ce_loss
        
        if self.alpha is not None:
            alpha_t = self.alpha[targets]
            loss = alpha_t * loss
            
        return loss.mean()


# ─── Training for one epoch ──────────────────────────────────────────
def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    max_grad_norm: float = 1.0,
) -> tuple[float, float, float]:
    """Run one training epoch.
    Returns:
      - mean training loss
      - mean gradient norm
      - mean attention entropy
    """
    model.train()
    total_loss = 0.0
    total_grad_norm = 0.0
    total_entropy = 0.0
    num_batches = 0

    for flux, labels in loader:
        flux = flux.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(flux)
        loss = criterion(logits, labels)
        loss.backward()

        # Track attention entropy if available
        if getattr(model, "last_attention_weights", None) is not None:
            total_entropy += compute_attention_entropy(model.last_attention_weights)

        # Track gradient norm before clipping
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += p.grad.detach().data.norm(2).item() ** 2
        grad_norm = grad_norm ** 0.5
        total_grad_norm += grad_norm

        # Gradient clipping
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_grad_norm)

        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    mean_loss = total_loss / max(num_batches, 1)
    mean_grad_norm = total_grad_norm / max(num_batches, 1)
    mean_entropy = total_entropy / max(num_batches, 1)

    return mean_loss, mean_grad_norm, mean_entropy


# ─── Validation ──────────────────────────────────────────────────────
@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    collect_predictions: bool = False,
) -> dict:
    """Evaluate model on validation set.
    Returns validation loss, accuracy, and attention entropy.
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    total_entropy = 0.0
    num_batches = 0
    
    per_class_correct: dict[int, int] = defaultdict(int)
    per_class_total: dict[int, int] = defaultdict(int)
    all_preds: list[int] = []
    all_labels: list[int] = []

    for flux, labels in loader:
        flux = flux.to(device)
        labels = labels.to(device)

        logits = model(flux)
        loss = criterion(logits, labels)

        total_loss += loss.item()
        num_batches += 1

        if getattr(model, "last_attention_weights", None) is not None:
            total_entropy += compute_attention_entropy(model.last_attention_weights)

        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        preds_list = preds.cpu().tolist()
        labels_list = labels.cpu().tolist()

        for pred, label in zip(preds_list, labels_list):
            per_class_total[label] += 1
            if pred == label:
                per_class_correct[label] += 1

        if collect_predictions:
            all_preds.extend(preds_list)
            all_labels.extend(labels_list)

    result = {
        "val_loss": total_loss / max(num_batches, 1),
        "val_accuracy": correct / max(total, 1),
        "val_entropy": total_entropy / max(num_batches, 1),
        "per_class_correct": dict(per_class_correct),
        "per_class_total": dict(per_class_total),
    }
    if collect_predictions:
        result["all_preds"] = all_preds
        result["all_labels"] = all_labels
    return result


# ─── Subgroup Evaluation ──────────────────────────────────────────────
@torch.no_grad()
def evaluate_subgroups(model: nn.Module, dataset: ASTRADataset, device: torch.device) -> dict:
    """Evaluate predictions on subgroups of catalog-period stars vs BLS-fallback stars."""
    model.eval()
    catalog_preds, catalog_labels = [], []
    bls_preds, bls_labels = [], []

    for idx, sample in enumerate(dataset._samples):
        flux_path = sample["flux_path"]
        with open(flux_path.parent / "metadata.json", "r") as f:
            meta = json.load(f)
        period_source = meta.get("period_source", "unknown")

        flux, label = dataset[idx]
        flux = flux.unsqueeze(0).to(device)  # (1, C, 1000)

        logits = model(flux)
        pred = logits.argmax(dim=1).item()

        if period_source == "catalog":
            catalog_preds.append(pred)
            catalog_labels.append(label.item())
        elif period_source == "BLS":
            bls_preds.append(pred)
            bls_labels.append(label.item())

    # Calculate accuracies
    cat_acc = 0.0
    if catalog_labels:
        cat_acc = sum(p == l for p, l in zip(catalog_preds, catalog_labels)) / len(catalog_labels)

    bls_acc = 0.0
    if bls_labels:
        bls_acc = sum(p == l for p, l in zip(bls_preds, bls_labels)) / len(bls_labels)

    return {
        "catalog": {
            "accuracy": cat_acc,
            "count": len(catalog_labels),
            "preds": catalog_preds,
            "labels": catalog_labels,
        },
        "bls": {
            "accuracy": bls_acc,
            "count": len(bls_labels),
            "preds": bls_preds,
            "labels": bls_labels,
        }
    }


# ─── Diagnostics ─────────────────────────────────────────────────────
def save_diagnostics(
    all_labels: list[int],
    all_preds: list[int],
    history: dict,
    save_dir: Path,
    tag: str,
) -> None:
    """Save confusion matrix, classification report, and curves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import classification_report, confusion_matrix

    class_names = CLASS_NAMES

    # 1. Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(NUM_CLASSES)))
    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        square=True,
        linewidths=0.5,
    )
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.set_title(f"ASTRA Transformer ({tag}) — Confusion Matrix")
    plt.tight_layout()
    cm_path = save_dir / f"confusion_matrix_transformer_{tag}.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)
    logger.info("Confusion matrix saved → %s", cm_path)

    # 2. Classification Report
    report = classification_report(
        all_labels,
        all_preds,
        target_names=class_names,
        labels=list(range(NUM_CLASSES)),
        zero_division=0,
    )
    report_path = save_dir / f"classification_report_transformer_{tag}.txt"
    report_path.write_text(report)
    logger.info("Classification report saved → %s", report_path)
    print(f"\n  Classification Report ({tag}):")
    print(report)

    # 3. Training Curves (with attention entropy)
    epochs = history.get("epochs", [])
    if epochs:
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

        # Loss curves
        ax1.plot(epochs, history["train_loss"], label="Train Loss", linewidth=2)
        ax1.plot(epochs, history["val_loss"], label="Val Loss", linewidth=2)
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Loss")
        ax1.set_title("Loss Curves")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Accuracy curve
        ax2.plot(epochs, history["val_accuracy"], label="Val Accuracy", linewidth=2, color="green")
        best_epoch = history.get("best_epoch", 0)
        best_acc = history.get("best_val_accuracy", 0)
        if best_epoch > 0:
            ax2.axvline(x=best_epoch, color="red", linestyle="--", alpha=0.5,
                        label=f"Best (ep {best_epoch}, {best_acc:.4f})")
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Accuracy")
        ax2.set_title("Validation Accuracy")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Attention Entropy Curve
        ax3.plot(epochs, history.get("train_entropy", [0]*len(epochs)), label="Train Entropy", linewidth=2, color="purple")
        ax3.plot(epochs, history.get("val_entropy", [0]*len(epochs)), label="Val Entropy", linewidth=2, color="orange")
        ax3.set_xlabel("Epoch")
        ax3.set_ylabel("Entropy (nats)")
        ax3.set_title("Attention Entropy")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        curves_path = save_dir / f"training_curves_transformer_{tag}.png"
        fig.savefig(curves_path, dpi=150)
        plt.close(fig)
        logger.info("Training curves saved → %s", curves_path)


# ─── Main training runner ─────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Train Hybrid Transformer on ASTRA variable star dataset.")
    parser.add_argument(
        "--variant", 
        type=str, 
        default="shared", 
        choices=["separate", "shared", "cross", "only", "shared_no_folded", "shared_no_folded_matched"]
    )
    parser.add_argument("--epochs", type=int, default=50, help="Epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--data-dir", type=str, default="data/processed")
    parser.add_argument("--augment", action="store_true", help="Enable augmentations")
    parser.add_argument("--pilot", action="store_true", help="Run 5-epoch pilot experiment")
    parser.add_argument("--tag", type=str, default="")
    args = parser.parse_args()

    # Enforce strict determinism at seed 42
    set_deterministic_seeds(42)

    # Paths
    data_dir = PROJECT_ROOT / args.data_dir
    try:
        assert_phase6_training_allowed(data_dir)
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)

    save_dir = PROJECT_ROOT / "models" / "saved"
    save_dir.mkdir(parents=True, exist_ok=True)

    variant = args.variant
    tag = args.tag if args.tag else variant
    use_folded = (variant not in ("only", "shared_no_folded", "shared_no_folded_matched"))
    
    # ── Device selection ──
    device = get_device()

    # ── Dataset ──
    train_dataset = ASTRADataset(data_dir=data_dir, split="train", use_folded=use_folded, augment=args.augment)
    val_dataset = ASTRADataset(data_dir=data_dir, split="val", use_folded=use_folded, augment=False)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # ── Model ──
    model = HybridTransformer(variant=variant, num_classes=NUM_CLASSES).to(device)
    params = HybridTransformer.count_parameters(model)

    print("=" * 70)
    print(f"  ASTRA HybridTransformer — Variant: {variant.upper()}")
    print("=" * 70)
    print(f"  Parameter Count:   {params['total']:,}")
    print(f"  Inputs:            Raw (1000) {'+ Folded (1000)' if use_folded else ''}")
    print(f"  Device:            {device}")
    print(f"  Pilot Mode:        {args.pilot}")
    print(f"  Augmentation:      {args.augment}")
    print()

    # ── Optimizer, Scheduler, and regularized Focal Loss ──
    class_weights = train_dataset.class_weights.to(device)
    criterion = RegularizedFocalLoss(alpha=class_weights, gamma=2.0, label_smoothing=0.1)
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-3)
    epochs_to_run = 5 if args.pilot else args.epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs_to_run)

    history = {
        "epochs": [],
        "train_loss": [],
        "train_grad_norm": [],
        "train_entropy": [],
        "val_loss": [],
        "val_accuracy": [],
        "val_entropy": [],
        "gpu_mem_mb": [],
        "best_epoch": 0,
        "best_val_accuracy": 0.0,
        "model_params": params["total"],
    }

    best_val_acc = 0.0
    best_epoch = 0
    start_time = time.time()

    print(f"{'Epoch':>5} │ {'Train Loss':>10} │ {'Val Loss':>9} │ {'Val Acc':>7} │ {'Grad Norm':>9} │ {'Ent (T)':>7} │ {'Ent (V)':>7} │ {'GPU Mem':>7} │")
    print("─" * 87)

    for epoch in range(1, epochs_to_run + 1):
        # 1. Train
        train_loss, train_grad_norm, train_entropy = train_one_epoch(
            model, train_loader, criterion, optimizer, device, max_grad_norm=1.0
        )

        # 2. Validate
        val_results = validate(model, val_loader, criterion, device)
        val_loss = val_results["val_loss"]
        val_acc = val_results["val_accuracy"]
        val_entropy = val_results["val_entropy"]

        # Track GPU memory
        gpu_mem = get_gpu_memory_mb()

        # Step scheduler
        scheduler.step()

        # Append history
        history["epochs"].append(epoch)
        history["train_loss"].append(round(train_loss, 6))
        history["train_grad_norm"].append(round(train_grad_norm, 6))
        history["train_entropy"].append(round(train_entropy, 6))
        history["val_loss"].append(round(val_loss, 6))
        history["val_accuracy"].append(round(val_acc, 6))
        history["val_entropy"].append(round(val_entropy, 6))
        history["gpu_mem_mb"].append(round(gpu_mem, 2))

        is_best = val_acc > best_val_acc
        marker = ""
        if is_best and not args.pilot:
            best_val_acc = val_acc
            best_epoch = epoch
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_accuracy": val_acc,
                "val_loss": val_loss,
                "class_names": CLASS_NAMES,
                "num_classes": NUM_CLASSES,
                "model_params": params["total"],
                "variant": variant,
                "use_folded": use_folded,
            }
            torch.save(checkpoint, save_dir / f"best_star_transformer_{tag}.pt")
            marker = " ★"

        print(
            f"{epoch:5d} │ {train_loss:10.6f} │ {val_loss:9.6f} │ {val_acc:7.4f} │ {train_grad_norm:9.4f} │ {train_entropy:7.3f} │ {val_entropy:7.3f} │ {gpu_mem:6.1f}M │{marker}"
        )

        # Safety Check for Pilots (abort conditions)
        if args.pilot:
            # Check for gradient explosion
            if math.isnan(train_loss) or train_grad_norm > 100.0:
                print(f"\n❌ PILOT ABORTED: Gradients exploded! Grad Norm: {train_grad_norm:.2f}, Loss: {train_loss}")
                sys.exit(2)
            # Check for entropy collapse (too small attention entropy)
            if train_entropy < 0.05 and epoch >= 3:
                print(f"\n❌ PILOT ABORTED: Attention entropy collapsed! Entropy: {train_entropy:.4f}")
                sys.exit(3)
            # Check for validation divergence
            if epoch >= 3 and val_loss > 4.0 * history["val_loss"][0]:
                print(f"\n❌ PILOT ABORTED: Validation loss diverged rapidly! Initial: {history['val_loss'][0]:.4f}, Current: {val_loss:.4f}")
                sys.exit(4)

    elapsed_time = time.time() - start_time

    if args.pilot:
        print(f"\n✅ Pilot experiment for variant '{variant}' completed successfully in {elapsed_time:.1f}s.")
        print(f"   Final Train Loss:       {train_loss:.6f}")
        print(f"   Final Val Loss:         {val_loss:.6f}")
        print(f"   Final Train Entropy:    {train_entropy:.4f}")
        print(f"   Final Val Entropy:      {val_entropy:.4f}")
        print(f"   Peak GPU Memory:        {max(history['gpu_mem_mb']):.2f} MB")
        return

    # Full Run Complete
    history["best_epoch"] = best_epoch
    history["best_val_accuracy"] = round(best_val_acc, 6)

    # Save training history
    history_path = save_dir / f"training_history_transformer_{tag}.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n{'─' * 87}")
    print(f"  Training Complete — Best Val Acc: {best_val_acc:.4f} (Epoch {best_epoch})")
    print(f"  Checkpoints saved to: models/saved/best_star_transformer_{tag}.pt")
    
    # ── Evaluate Subgroups ──
    print(f"\n  Running subgroup evaluation...")
    # Load best checkpoint
    checkpoint_file = save_dir / f"best_star_transformer_{tag}.pt"
    ckpt = torch.load(checkpoint_file, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    
    subgroups = evaluate_subgroups(model, val_dataset, device)
    print(f"    Catalog Stars Subgroup Accuracy: {subgroups['catalog']['accuracy']:.4f} ({subgroups['catalog']['count']} stars)")
    print(f"    BLS Fallback Stars Subgroup Accuracy: {subgroups['bls']['accuracy']:.4f} ({subgroups['bls']['count']} stars)")

    # Save subgroup evaluation results to history json
    history["subgroup_evaluation"] = {
        "catalog_accuracy": subgroups["catalog"]["accuracy"],
        "catalog_count": subgroups["catalog"]["count"],
        "bls_accuracy": subgroups["bls"]["accuracy"],
        "bls_count": subgroups["bls"]["count"],
    }
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    # ── Save Environment Metadata ──
    split_hash = "unknown"
    split_meta_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "split_metadata.json"
    split_hash = "unknown"
    if split_meta_path.exists():
        try:
            with open(split_meta_path) as f:
                split_hash = json.load(f).get("split_hash", "unknown")
        except Exception:
            pass

    git_commit = "unknown"
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            git_commit = res.stdout.strip()
    except Exception:
        pass

    ckpt_sha256 = get_file_sha256(checkpoint_file)

    # Calculate dataset manifest hash
    manifest_path = PROJECT_ROOT / "data" / "phase6" / "scientific_dataset_freeze_v2.csv"
    manifest_sha256 = get_file_sha256(manifest_path)

    # Split files hashes
    train_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "train_ids.json"
    val_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "val_ids.json"
    test_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "test_ids.json"
    from datetime import datetime
    
    split_hashes = {
        "train": get_file_sha256(train_split_path),
        "val": get_file_sha256(val_split_path),
        "test": get_file_sha256(test_split_path)
    }

    exp_metadata = {
        "variant": variant,
        "seed": 42,
        "device": str(device),
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "parameter_count": params["total"],
        "git_commit": git_commit,
        "dataset_fingerprint_hash": manifest_sha256,
        "split_hash_root": split_hash,
        "split_hashes": split_hashes,
        "checkpoint_sha256": ckpt_sha256,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    metadata_file = save_dir / f"experiment_metadata_{tag}.json"
    with open(metadata_file, "w") as f:
        json.dump(exp_metadata, f, indent=2)
    logger.info("Saved experiment metadata to %s", metadata_file)

    # Update consolidated experiment_metadata.json
    consolidated_path = save_dir / "experiment_metadata.json"
    consolidated_data = {}
    if consolidated_path.exists():
        try:
            with open(consolidated_path, "r") as f:
                consolidated_data = json.load(f)
        except Exception:
            pass
    consolidated_data[variant] = exp_metadata
    with open(consolidated_path, "w") as f:
        json.dump(consolidated_data, f, indent=2)
    logger.info("Updated consolidated experiment metadata at %s", consolidated_path)

    # ── Test Set Lock Protection Assertion ──
    from training.dataset import TEST_SET_ACCESSED
    assert not TEST_SET_ACCESSED, "Leakage detected: Test dataset was accessed during training!"
    print("\n🔒 Test set lock protection verified: TEST_SET_ACCESSED is FALSE.")

    # ── Post-training diagnostics ──
    print(f"\n  Generating diagnostics (confusion matrix, classification report)...")
    final_val = validate(model, val_loader, criterion, device, collect_predictions=True)
    save_diagnostics(
        all_labels=final_val["all_labels"],
        all_preds=final_val["all_preds"],
        history=history,
        save_dir=save_dir,
        tag=tag,
    )
    print(f"\n✅ Variant '{variant}' evaluation completed.")



if __name__ == "__main__":
    main()
