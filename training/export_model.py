"""
ASTRA — Model Export and Deployment Verification Script.

Exports the production Hybrid Shared Transformer model to TorchScript and ONNX,
benchmarks CPU and MPS latencies, and writes deployment_report.md.
"""

from __future__ import annotations

import sys
import time
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.models.hybrid_transformer import HybridTransformer

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

ARTIFACT_DIR = Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/6213b34b-7bbc-4ddd-bf18-dae93ae7cb54")
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "saved" / "best_star_transformer_shared.pt"


def main() -> None:
    print("=" * 70)
    print("  ASTRA Model Export & Deployment Benchmarking")
    print("=" * 70)
    
    # 1. Load PyTorch Checkpoint
    if not CHECKPOINT_PATH.exists():
        print(f"❌ ERROR: Checkpoint not found at {CHECKPOINT_PATH}.")
        sys.exit(1)
        
    device = torch.device("cpu") # export is safest on CPU first
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    model = HybridTransformer(variant=ckpt["variant"], num_classes=ckpt["num_classes"])
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    # Dummy input representing (batch_size=1, channels=2, sequence_length=1000)
    dummy_input = torch.randn(1, 2, 1000, dtype=torch.float32)
    
    # 2. Export to TorchScript (JIT Trace)
    print("Exporting model to TorchScript...")
    ts_path = PROJECT_ROOT / "models" / "saved" / "best_star_transformer_shared.torchscript"
    with torch.no_grad():
        traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save(ts_path)
    print(f"  ✅ TorchScript exported successfully → {ts_path}")
    
    # 3. Export to ONNX
    print("Exporting model to ONNX...")
    onnx_path = PROJECT_ROOT / "models" / "saved" / "best_star_transformer_shared.onnx"
    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
        )
    print(f"  ✅ ONNX exported successfully → {onnx_path}")
    
    # 4. Verification Check
    print("Verifying exported formats...")
    # Load TorchScript
    model_ts = torch.jit.load(ts_path)
    model_ts.eval()
    
    with torch.no_grad():
        out_pt = model(dummy_input)
        out_ts = model_ts(dummy_input)
        
    diff_ts = torch.max(torch.abs(out_pt - out_ts)).item()
    print(f"  Max output difference (PyTorch vs TorchScript): {diff_ts:.2e}")
    assert diff_ts < 1e-5, "TorchScript outputs do not match PyTorch baseline!"
    
    # Load ONNX using ONNX Runtime (if available)
    onnx_runtime_available = False
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(onnx_path))
        input_name = sess.get_inputs()[0].name
        out_onnx = sess.run(None, {input_name: dummy_input.numpy()})[0]
        diff_onnx = np.max(np.abs(out_pt.numpy() - out_onnx))
        print(f"  Max output difference (PyTorch vs ONNX):        {diff_onnx:.2e}")
        assert diff_onnx < 1e-5, "ONNX outputs do not match PyTorch baseline!"
        onnx_runtime_available = True
    except ImportError:
        print("  ⚠️ ONNX Runtime not installed. Bypassing ONNX output check.")
        
    # 5. Benchmarking Latency & Throughput (CPU and MPS)
    print("\nBenchmarking Latency & Throughput...")
    
    num_iterations = 200
    benchmark_results = {}
    
    devices = [torch.device("cpu")]
    if torch.backends.mps.is_available():
        devices.append(torch.device("mps"))
        
    for dev in devices:
        print(f"  Target Device: {dev}")
        model_bench = model.to(dev)
        inp_bench = dummy_input.to(dev)
        
        # Warmup
        for _ in range(20):
            _ = model_bench(inp_bench)
        if dev.type == "mps":
            torch.mps.synchronize()
            
        t0 = time.perf_counter()
        for _ in range(num_iterations):
            _ = model_bench(inp_bench)
        if dev.type == "mps":
            torch.mps.synchronize()
        dt = time.perf_counter() - t0
        
        avg_latency_ms = (dt / num_iterations) * 1000
        throughput = num_iterations / dt
        
        benchmark_results[dev.type] = {
            "avg_latency_ms": avg_latency_ms,
            "throughput_seq_sec": throughput
        }
        print(f"    Avg Latency:  {avg_latency_ms:.2f} ms")
        print(f"    Throughput:   {throughput:.1f} inferences/sec")
        
    # Move model back to CPU
    model.to(torch.device("cpu"))
    
    # 6. Generate deployment_report.md
    report_lines = [
        "# ASTRA — Deployment & Export Verification Report",
        "",
        "This report details the export and production-level benchmarking of the ASTRA Hybrid Shared Transformer model.",
        "",
        "## 1. Export Formats Status",
        "",
        "The model has been successfully compiled and verified in the following deployment formats:",
        f"- **TorchScript JIT Traced Checkpoint**: [best_star_transformer_shared.torchscript](file://{ts_path})",
        f"- **ONNX Serialized Model**: [best_star_transformer_shared.onnx](file://{onnx_path})",
        "",
        "| Export Format | Output Equivalence Check (Tolerance: 1.0e-5) | Status |",
        "| :--- | :---: | :---: |",
        f"| **TorchScript** | Max absolute difference: `{diff_ts:.2e}` | ✅ Verified |",
    ]
    if onnx_runtime_available:
        report_lines.append(f"| **ONNX** | Max absolute difference: `{diff_onnx:.2e}` | ✅ Verified |")
    else:
        report_lines.append("| **ONNX** | ONNX Runtime not installed for check | ⚠️ Exported |")
        
    report_lines.extend([
        "",
        "## 2. Latency & Throughput Benchmark",
        "",
        "Benchmarking was performed with a single-sample batch (`batch_size=1`) over 200 repeated inferences:",
        "",
        "| Device | Average Latency (ms) | Throughput (Inferences/sec) | Latency Target (< 15.0ms) |",
        "| :--- | :---: | :---: | :---: |",
        f"| **CPU** | {benchmark_results['cpu']['avg_latency_ms']:.2f} ms | {benchmark_results['cpu']['throughput_seq_sec']:.1f} | {'✅ Met' if benchmark_results['cpu']['avg_latency_ms'] < 15.0 else '⚠️ Exceeded'} |",
    ])
    if "mps" in benchmark_results:
        report_lines.append(
            f"| **MPS (Apple Silicon GPU)** | {benchmark_results['mps']['avg_latency_ms']:.2f} ms | {benchmark_results['mps']['throughput_seq_sec']:.1f} | "
            f"{'✅ Met' if benchmark_results['mps']['avg_latency_ms'] < 15.0 else '⚠️ Exceeded'} |"
        )
        
    report_lines.extend([
        "",
        "## 3. Deployment Inference Guide",
        "",
        "A command-line script is provided to run local inferences using the PyTorch or TorchScript models:",
        "- Script Path: [predict.py](file:///Users/soumyadebtripathy/ASTRA%20—%20Automated%20Stellar%20Transient%20Recognition%20&%20Analysis/training/predict.py)",
        "",
        "```bash",
        "python training/predict.py --input data/processed/TIC_109718459/",
        "```",
    ])
    
    report_path = ARTIFACT_DIR / "deployment_report.md"
    report_path.write_text("\n".join(report_lines) + "\n")
    print(f"Deployment report saved successfully → {report_path}")


if __name__ == "__main__":
    main()
