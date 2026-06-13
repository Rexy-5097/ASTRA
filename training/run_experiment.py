#!/usr/bin/env python3
"""
ASTRA — Controlled retraining experiment.

Orchestrates two training runs to compare:
  A) Raw-only model with augmentations
  B) Dual-branch (raw + phase-folded) model with augmentations

After both runs complete, compiles a Markdown comparison report at
  models/saved/experiment_summary.md

Usage:
    python training/run_experiment.py
    python training/run_experiment.py --epochs 60 --batch-size 32

Requirements:
    Preprocessed dataset with both raw and folded flux arrays.
    Run `python pipeline/batch_process.py --force` first if folded
    arrays are missing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PYTHON = sys.executable
TRAIN_SCRIPT = str(PROJECT_ROOT / "training" / "train_cnn.py")
SAVE_DIR = PROJECT_ROOT / "models" / "saved"


def run_training(
    *,
    tag: str,
    epochs: int,
    batch_size: int,
    lr: float,
    use_folded: bool,
    augment: bool,
) -> dict:
    """Launch a single training run as a subprocess and return results."""
    cmd = [
        PYTHON, TRAIN_SCRIPT,
        "--epochs", str(epochs),
        "--batch-size", str(batch_size),
        "--lr", str(lr),
        "--tag", tag,
    ]
    if use_folded:
        cmd.append("--use-folded")
    if augment:
        cmd.append("--augment")

    print(f"\n{'='*70}")
    print(f"  EXPERIMENT: {tag}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=False,  # stream output live
    )

    if result.returncode != 0:
        print(f"\n❌ Training run '{tag}' failed with exit code {result.returncode}")
        return {"tag": tag, "status": "failed", "returncode": result.returncode}

    # Load training history
    history_path = SAVE_DIR / f"training_history_{tag}.json"
    if history_path.exists():
        with open(history_path) as f:
            history = json.load(f)
    else:
        history = {}

    # Load classification report
    report_path = SAVE_DIR / f"classification_report_{tag}.txt"
    report_text = report_path.read_text() if report_path.exists() else "N/A"

    return {
        "tag": tag,
        "status": "success",
        "best_epoch": history.get("best_epoch", "?"),
        "best_val_accuracy": history.get("best_val_accuracy", 0.0),
        "model_params": history.get("model_params", "?"),
        "config": history.get("config", {}),
        "classification_report": report_text,
        "history_path": str(history_path),
    }


def generate_summary(results: list[dict], save_dir: Path) -> Path:
    """Create a Markdown comparison report from experiment results."""
    summary_path = save_dir / "experiment_summary.md"

    lines = [
        "# ASTRA — Experiment Comparison Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Experiment Overview",
        "",
        "| Experiment | Mode | Augment | Best Epoch | Val Accuracy | Params |",
        "|------------|------|---------|------------|--------------|--------|",
    ]

    for r in results:
        if r["status"] == "success":
            mode = "Dual-branch" if r["config"].get("use_folded") else "Raw-only"
            aug = "✅" if r["config"].get("augment") else "❌"
            acc = r["best_val_accuracy"]
            lines.append(
                f"| {r['tag']} | {mode} | {aug} | "
                f"{r['best_epoch']} | {acc:.4f} ({acc*100:.2f}%) | "
                f"{r['model_params']:,} |"
            )
        else:
            lines.append(f"| {r['tag']} | FAILED | - | - | - | - |")

    # Per-experiment classification reports
    lines.extend(["", "---", ""])
    for r in results:
        if r["status"] == "success":
            lines.extend([
                f"## Classification Report — `{r['tag']}`",
                "",
                "```",
                r.get("classification_report", "N/A").strip(),
                "```",
                "",
            ])

    # Comparison analysis
    successful = [r for r in results if r["status"] == "success"]
    if len(successful) >= 2:
        a = successful[0]
        b = successful[1]
        diff = b["best_val_accuracy"] - a["best_val_accuracy"]
        sign = "+" if diff >= 0 else ""
        lines.extend([
            "---",
            "",
            "## Analysis",
            "",
            f"- **{a['tag']}** accuracy: {a['best_val_accuracy']:.4f}",
            f"- **{b['tag']}** accuracy: {b['best_val_accuracy']:.4f}",
            f"- **Delta**: {sign}{diff:.4f} ({sign}{diff*100:.2f}%)",
            "",
            "> Compare the per-class precision/recall above to assess whether "
            "phase-folding reduced Cepheid vs RR Lyrae confusion specifically.",
            "",
            "Confusion matrices saved to:",
            f"- `confusion_matrix_{a['tag']}.png`",
            f"- `confusion_matrix_{b['tag']}.png`",
        ])

    summary_path.write_text("\n".join(lines) + "\n")
    print(f"\n📊 Experiment summary saved → {summary_path}")
    return summary_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ASTRA controlled retraining experiment (raw vs dual-branch)."
    )
    parser.add_argument("--epochs", type=int, default=50, help="Epochs per run")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    args = parser.parse_args()

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  ASTRA — Controlled Retraining Experiment")
    print("=" * 70)
    print(f"  Epochs per run: {args.epochs}")
    print(f"  Batch size:     {args.batch_size}")
    print(f"  Learning rate:  {args.lr}")
    print()

    results: list[dict] = []

    # Experiment A: Raw-only + augmentation
    result_a = run_training(
        tag="raw_aug",
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        use_folded=False,
        augment=True,
    )
    results.append(result_a)

    # Experiment B: Dual-branch + augmentation
    result_b = run_training(
        tag="dual_aug",
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        use_folded=True,
        augment=True,
    )
    results.append(result_b)

    # Generate comparison report
    generate_summary(results, SAVE_DIR)

    print("\n✅ Experiment complete!")


if __name__ == "__main__":
    main()
