"""
ASTRA — Training script for StarCNN stellar light curve classifier.

Usage:
    python training/train_cnn.py
    python training/train_cnn.py --epochs 100 --batch-size 64 --lr 5e-4
    python training/train_cnn.py --data-dir data/processed --epochs 30
    python training/train_cnn.py --use-folded --augment   # dual-branch + augmentation

Features:
    • MPS (Apple Silicon) or CPU device selection — never CUDA
    • Focal loss with inverse-frequency class weights
    • AdamW optimizer with cosine annealing LR schedule
    • Gradient clipping (max_norm=1.0)
    • Per-class accuracy tracking
    • Best-model checkpointing by validation accuracy
    • Training history exported to JSON
    • Post-training diagnostics: confusion matrix, classification report,
      training curves (loss & accuracy)
    • Optional dual-branch mode (raw + phase-folded) and data augmentations
"""

import argparse
import hashlib
import json
import logging
import random
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from torch.utils.data import DataLoader

from data.labels import CLASS_NAMES, LABEL_TO_NAME, NUM_CLASSES
from pipeline.phase6_utils import assert_phase6_training_allowed
from training.dataset import ASTRADataset
from training.focal_loss import FocalLoss
from training.models.star_cnn import StarCNN

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


def get_file_sha256(path: Path) -> str:
    """Compute the SHA256 checksum of a file for experiment reproducibility audits."""
    if not path.exists():
        return "file_not_found"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()



# ─── Device selection ────────────────────────────────────────────────
def get_device() -> torch.device:
    """Select MPS if available, otherwise CPU. Never CUDA."""
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        logger.info("Using device: MPS (Apple Silicon GPU)")
    else:
        device = torch.device("cpu")
        logger.info("Using device: CPU")
    return device


# ─── Training for one epoch ──────────────────────────────────────────
def train_one_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    max_grad_norm: float = 1.0,
) -> float:
    """Run one training epoch. Returns mean training loss."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    for flux, labels in loader:
        flux = flux.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(flux)
        loss = criterion(logits, labels)
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_grad_norm)

        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    return total_loss / max(num_batches, 1)


# ─── Validation ──────────────────────────────────────────────────────
@torch.no_grad()
def validate(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    device: torch.device,
    collect_predictions: bool = False,
) -> dict:
    """Evaluate model on validation set.

    Returns dict with keys: val_loss, val_accuracy, per_class_correct,
    per_class_total.  When *collect_predictions* is True, also returns
    'all_preds' and 'all_labels' lists for downstream diagnostics.
    """
    model.eval()
    total_loss = 0.0
    num_batches = 0
    correct = 0
    total = 0
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
        "per_class_correct": dict(per_class_correct),
        "per_class_total": dict(per_class_total),
    }
    if collect_predictions:
        result["all_preds"] = all_preds
        result["all_labels"] = all_labels
    return result


# ─── Diagnostics ─────────────────────────────────────────────────────
def save_diagnostics(
    all_labels: list[int],
    all_preds: list[int],
    history: dict,
    save_dir: Path,
    tag: str = "",
) -> None:
    """Generate and save post-training diagnostic plots and reports.

    Outputs:
      - confusion_matrix{tag}.png
      - classification_report{tag}.txt
      - training_curves{tag}.png
    """
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import classification_report, confusion_matrix

    class_names = CLASS_NAMES
    suffix = f"_{tag}" if tag else ""

    # ── 1. Confusion Matrix ──────────────────────────────────────────
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
    ax.set_title(f"ASTRA StarCNN — Confusion Matrix{' (' + tag + ')' if tag else ''}")
    plt.tight_layout()
    cm_path = save_dir / f"confusion_matrix{suffix}.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)
    logger.info("Confusion matrix saved → %s", cm_path)

    # ── 2. Classification Report ─────────────────────────────────────
    report = classification_report(
        all_labels,
        all_preds,
        target_names=class_names,
        labels=list(range(NUM_CLASSES)),
        zero_division=0,
    )
    report_path = save_dir / f"classification_report{suffix}.txt"
    report_path.write_text(report)
    logger.info("Classification report saved → %s", report_path)
    print(f"\n  Classification Report{' (' + tag + ')' if tag else ''}:")
    print(report)

    # ── 3. Training Curves ───────────────────────────────────────────
    epochs = history.get("epochs", [])
    if epochs:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Loss curves
        ax1.plot(epochs, history["train_loss"], label="Train Loss", linewidth=2)
        ax1.plot(epochs, history["val_loss"], label="Val Loss", linewidth=2)
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Loss")
        ax1.set_title("Training & Validation Loss")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Accuracy curve
        ax2.plot(epochs, history["val_accuracy"], label="Val Accuracy",
                 linewidth=2, color="green")
        best_epoch = history.get("best_epoch", 0)
        best_acc = history.get("best_val_accuracy", 0)
        if best_epoch > 0:
            ax2.axvline(x=best_epoch, color="red", linestyle="--", alpha=0.5,
                        label=f"Best (epoch {best_epoch}, {best_acc:.4f})")
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Accuracy")
        ax2.set_title("Validation Accuracy")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        curves_path = save_dir / f"training_curves{suffix}.png"
        fig.savefig(curves_path, dpi=150)
        plt.close(fig)
        logger.info("Training curves saved → %s", curves_path)


# ─── Main training loop ─────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train StarCNN on ASTRA stellar light curve dataset."
    )
    parser.add_argument(
        "--epochs", type=int, default=50, help="Number of training epochs (default: 50)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Batch size (default: 32)"
    )
    parser.add_argument(
        "--lr", type=float, default=1e-3, help="Learning rate (default: 1e-3)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/processed",
        help="Path to processed data directory (default: data/processed)",
    )
    parser.add_argument(
        "--use-folded", action="store_true",
        help="Enable dual-branch mode (raw + phase-folded flux)",
    )
    parser.add_argument(
        "--augment", action="store_true",
        help="Enable stochastic data augmentations on training split",
    )
    parser.add_argument(
        "--tag", type=str, default="",
        help="Optional tag for output files (e.g. 'raw_only', 'dual')",
    )
    args = parser.parse_args()

    # Enforce strict determinism at seed 42
    set_deterministic_seeds(42)

    data_dir = PROJECT_ROOT / args.data_dir
    try:
        assert_phase6_training_allowed(data_dir)
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)

    save_dir = PROJECT_ROOT / "models" / "saved"
    save_dir.mkdir(parents=True, exist_ok=True)

    tag = args.tag
    use_folded = args.use_folded
    augment = args.augment

    print("=" * 70)
    print("  ASTRA — StarCNN Training")
    print("=" * 70)
    print(f"  Data directory:   {data_dir}")
    print(f"  Save directory:   {save_dir}")
    print(f"  Epochs:           {args.epochs}")
    print(f"  Batch size:       {args.batch_size}")
    print(f"  Learning rate:    {args.lr}")
    print(f"  Num classes:      {NUM_CLASSES}")
    print(f"  Dual-branch:      {use_folded}")
    print(f"  Augmentation:     {augment}")
    if tag:
        print(f"  Tag:              {tag}")
    print()

    # ── Device ───────────────────────────────────────────────────────
    device = get_device()

    # ── Data loading ─────────────────────────────────────────────────
    train_dataset = ASTRADataset(
        data_dir=data_dir, split="train",
        use_folded=use_folded, augment=augment,
    )
    val_dataset = ASTRADataset(
        data_dir=data_dir, split="val",
        use_folded=use_folded, augment=False,  # never augment validation
    )

    if len(train_dataset) == 0:
        print("\n❌ ERROR: Training dataset is empty.")
        print(f"   Looked in: {data_dir}")
        print("   Run the preprocessing pipeline first to generate TIC_* directories.")
        sys.exit(1)

    if len(val_dataset) == 0:
        print("\n❌ ERROR: Validation dataset is empty.")
        print("   Check val_fraction or increase dataset size.")
        sys.exit(1)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,  # MPS compatibility
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        drop_last=False,
    )

    # Print class distributions
    print("Train split class distribution:")
    train_counts = train_dataset.class_counts
    for name in CLASS_NAMES:
        print(f"  {name:20s}: {train_counts[name]:5d}")
    print(f"  {'TOTAL':20s}: {len(train_dataset):5d}")

    print("\nVal split class distribution:")
    val_counts = val_dataset.class_counts
    for name in CLASS_NAMES:
        print(f"  {name:20s}: {val_counts[name]:5d}")
    print(f"  {'TOTAL':20s}: {len(val_dataset):5d}")

    # ── Model ────────────────────────────────────────────────────────
    model = StarCNN(num_classes=NUM_CLASSES, use_folded=use_folded).to(device)
    params = StarCNN.count_parameters(model)
    mode_str = "dual-branch" if use_folded else "single-branch"
    print(f"\nModel ({mode_str}): {params['total']:,} total, {params['trainable']:,} trainable params")

    # ── Loss, optimizer, scheduler ───────────────────────────────────
    class_weights = train_dataset.class_weights.to(device)
    print(f"Class weights: {class_weights.cpu().tolist()}")

    criterion = FocalLoss(alpha=class_weights, gamma=2.0, reduction="mean")
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs
    )

    # ── Training history ─────────────────────────────────────────────
    history: dict = {
        "epochs": [],
        "train_loss": [],
        "val_loss": [],
        "val_accuracy": [],
        "learning_rate": [],
        "best_epoch": 0,
        "best_val_accuracy": 0.0,
        "model_params": params["total"],
        "device": str(device),
        "config": {
            "batch_size": args.batch_size,
            "lr": args.lr,
            "weight_decay": 1e-4,
            "gamma": 2.0,
            "max_grad_norm": 1.0,
            "num_epochs": args.epochs,
            "val_fraction": 0.2,
            "use_folded": use_folded,
            "augment": augment,
            "tag": tag,
        },
    }

    best_val_acc = 0.0
    best_epoch = 0
    best_per_class: dict = {}

    print(f"\n{'─' * 70}")
    print(f"{'Epoch':>6} │ {'Train Loss':>11} │ {'Val Loss':>10} │ {'Val Acc':>8} │ {'LR':>10} │")
    print(f"{'─' * 70}")

    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        # Train
        train_loss = train_one_epoch(
            model, train_loader, criterion, optimizer, device
        )

        # Validate
        val_results = validate(model, val_loader, criterion, device)
        val_loss = val_results["val_loss"]
        val_acc = val_results["val_accuracy"]

        # LR step
        current_lr = optimizer.param_groups[0]["lr"]
        scheduler.step()

        # Track history
        history["epochs"].append(epoch)
        history["train_loss"].append(round(train_loss, 6))
        history["val_loss"].append(round(val_loss, 6))
        history["val_accuracy"].append(round(val_acc, 6))
        history["learning_rate"].append(round(current_lr, 8))

        # Check for best model
        is_best = val_acc > best_val_acc
        marker = ""
        if is_best:
            best_val_acc = val_acc
            best_epoch = epoch
            best_per_class = {
                "correct": val_results["per_class_correct"],
                "total": val_results["per_class_total"],
            }
            marker = " ★"

            # Save best checkpoint
            suffix = f"_{tag}" if tag else ""
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_accuracy": val_acc,
                "val_loss": val_loss,
                "class_names": CLASS_NAMES,
                "num_classes": NUM_CLASSES,
                "model_params": params["total"],
                "use_folded": use_folded,
            }
            ckpt_name = f"best_star_cnn{suffix}.pt"
            torch.save(checkpoint, save_dir / ckpt_name)

        print(
            f"{epoch:6d} │ {train_loss:11.6f} │ {val_loss:10.6f} │ {val_acc:7.4f} │ {current_lr:10.2e} │{marker}"
        )

    elapsed = time.time() - start_time

    # Update history with best results
    history["best_epoch"] = best_epoch
    history["best_val_accuracy"] = round(best_val_acc, 6)

    # Save training history
    suffix = f"_{tag}" if tag else ""
    history_path = save_dir / f"training_history{suffix}.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    # ── Final summary ────────────────────────────────────────────────
    ckpt_name = f"best_star_cnn{suffix}.pt"
    print(f"{'─' * 70}")
    print(f"\n{'=' * 70}")
    print("  Training Complete — Summary")
    print(f"{'=' * 70}")
    print(f"  Total time:         {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print(f"  Best epoch:         {best_epoch}")
    print(f"  Best val accuracy:  {best_val_acc:.4f} ({best_val_acc * 100:.2f}%)")
    print(f"  Model saved to:     {save_dir / ckpt_name}")
    print(f"  History saved to:   {history_path}")

    if best_per_class:
        print(f"\n  Per-class accuracy (best epoch {best_epoch}):")
        for c in range(NUM_CLASSES):
            total_c = best_per_class["total"].get(c, 0)
            correct_c = best_per_class["correct"].get(c, 0)
            acc_c = correct_c / max(total_c, 1)
            print(
                f"    {LABEL_TO_NAME[c]:20s}: {correct_c:4d}/{total_c:4d} = {acc_c:.4f}"
            )

    # ── Post-training diagnostics ────────────────────────────────────
    # Reload the best checkpoint and run full-set validation
    print(f"\n{'─' * 70}")
    print("  Generating diagnostics (confusion matrix, classification report)...")
    ckpt = torch.load(save_dir / ckpt_name, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    final_val = validate(
        model, val_loader, criterion, device, collect_predictions=True
    )
    save_diagnostics(
        all_labels=final_val["all_labels"],
        all_preds=final_val["all_preds"],
        history=history,
        save_dir=save_dir,
        tag=tag,
    )

    # ── Test Set Lock Protection Assertion ──
    from training.dataset import TEST_SET_ACCESSED
    assert not TEST_SET_ACCESSED, "Leakage detected: Test dataset was accessed during training!"
    print("\n🔒 Test set lock protection verified: TEST_SET_ACCESSED is FALSE.")

    # ── Save Consolidated Experiment Metadata ──
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

    checkpoint_file = save_dir / ckpt_name
    ckpt_sha256 = get_file_sha256(checkpoint_file)

    # Calculate dataset manifest hash
    manifest_path = PROJECT_ROOT / "data" / "phase6" / "scientific_dataset_freeze_v2.csv"
    manifest_sha256 = get_file_sha256(manifest_path)

    # Split files hashes
    train_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "train_ids.json"
    val_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "val_ids.json"
    test_split_path = PROJECT_ROOT / "data" / "phase6" / "splits" / "test_ids.json"

    split_hashes = {
        "train": get_file_sha256(train_split_path),
        "val": get_file_sha256(val_split_path),
        "test": get_file_sha256(test_split_path)
    }

    exp_metadata = {
        "variant": tag if tag else "cnn_dual",
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
    consolidated_data[tag if tag else "cnn_dual"] = exp_metadata
    with open(consolidated_path, "w") as f:
        json.dump(consolidated_data, f, indent=2)
    logger.info("Updated consolidated experiment metadata at %s", consolidated_path)

    print("\n✅ Done!")



if __name__ == "__main__":
    main()
