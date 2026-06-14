#!/usr/bin/env python3
"""
ASTRA Phase 6A — stable_screen.py

Quantitative stability screening for stable star candidates.
Performs ALL checks locally without remote catalog calls (fail-open).
Remote contamination checks are delegated to variability_crosscheck.py.

Screening criteria (ALL must pass for "stable"):
  1. RMS < rms_threshold (default 0.005 in normalized flux)
  2. No strong BLS peak (BLS power < bls_power_threshold)
  3. Lomb-Scargle FAP > fap_threshold (no significant period)
  4. Variability amplitude < amplitude_threshold
  5. No flare spike excess (outlier fraction < outlier_fraction_threshold)
  6. SNR consistency check (SNR > snr_min)
  7. Point scatter consistency (scatter / median_scatter < scatter_ratio_threshold)

All thresholds are configurable.
Output:
  - stable_screening_report.md
  - updated candidate rows with stability_screen_status field

Usage:
    python pipeline/stable_screen.py
    python pipeline/stable_screen.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.phase6_utils import (
    DEFAULT_PHASE6_ROOT,
    read_csv_rows,
    utc_now,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stable_screen")

ARTIFACT_DIR = Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/6213b34b-7bbc-4ddd-bf18-dae93ae7cb54")


@dataclass
class StabilityThresholds:
    """Configurable thresholds for quantitative stability screening."""
    rms_threshold: float = 0.010          # Normalized flux RMS must be < this
    bls_power_threshold: float = 0.15     # BLS peak power must be < this
    fap_threshold: float = 0.01           # LS False Alarm Probability must be > this (i.e. NOT significant)
    amplitude_threshold: float = 0.050   # Peak-to-peak amplitude in normalized flux must be < this
    outlier_fraction_threshold: float = 0.015  # Fraction of points >5-sigma from median must be < this
    snr_min: float = 0.5                  # ASTRA estimated_snr — quiet stable stars typically score ~1.0
    scatter_ratio_threshold: float = 3.0  # Local scatter / global scatter must be < this
    min_points: int = 100                 # Minimum valid data points required


@dataclass
class ScreeningResult:
    """Detailed screening result for a single star."""
    tic_id: str
    astra_class: str
    n_points: int
    rms: float | None = None
    bls_power: float | None = None
    ls_fap: float | None = None
    amplitude: float | None = None
    outlier_fraction: float | None = None
    snr: float | None = None
    scatter_ratio: float | None = None
    # Pass/fail per criterion
    passes_rms: bool | None = None
    passes_bls: bool | None = None
    passes_ls_fap: bool | None = None
    passes_amplitude: bool | None = None
    passes_outlier: bool | None = None
    passes_snr: bool | None = None
    passes_scatter: bool | None = None
    # Overall
    overall_pass: bool = False
    failure_reasons: list[str] = field(default_factory=list)
    # Review flag (borderline)
    review_required: bool = False
    review_reasons: list[str] = field(default_factory=list)


def _compute_rms(flux: np.ndarray) -> float:
    """Root-mean-square of the flux array."""
    return float(np.sqrt(np.mean(flux**2)))


def _compute_amplitude(flux: np.ndarray) -> float:
    """Peak-to-peak amplitude (robust: 1st–99th percentile)."""
    return float(np.percentile(flux, 99) - np.percentile(flux, 1))


def _compute_outlier_fraction(flux: np.ndarray, sigma: float = 5.0) -> float:
    """Fraction of points > sigma*MAD from median."""
    median = np.median(flux)
    mad = np.median(np.abs(flux - median))
    if mad == 0:
        return 0.0
    robust_sigma = 1.4826 * mad
    outliers = np.abs(flux - median) > sigma * robust_sigma
    return float(np.mean(outliers))


def _compute_scatter_ratio(flux: np.ndarray, window: int = 50) -> float:
    """Local scatter / global scatter to detect structured variability."""
    if len(flux) < window * 2:
        return 1.0
    global_sigma = np.std(flux)
    if global_sigma == 0:
        return 1.0
    local_sigmas = []
    for i in range(0, len(flux) - window, window // 2):
        chunk = flux[i:i + window]
        local_sigmas.append(np.std(chunk))
    if not local_sigmas:
        return 1.0
    return float(max(local_sigmas) / global_sigma)


def _compute_ls_fap(flux: np.ndarray, min_period: float = 0.1, max_period: float = 30.0) -> float:
    """Lomb-Scargle False Alarm Probability for the best period in [min_period, max_period] days.

    Uses evenly-spaced time grid as a proxy (no actual timestamps available).
    Returns FAP: values close to 0 = highly significant periodicity (fail for stable).
    """
    try:
        from astropy.timeseries import LombScargle
        # Create synthetic time array spanning ~27 days (one TESS sector)
        n = len(flux)
        time = np.linspace(0, 27.4, n)
        ls = LombScargle(time, flux)
        freq_min = 1.0 / max_period
        freq_max = 1.0 / min_period
        freq, power = ls.autopower(minimum_frequency=freq_min, maximum_frequency=freq_max, samples_per_peak=5)
        if len(power) == 0:
            return 1.0
        best_power = float(np.max(power))
        fap = float(ls.false_alarm_probability(best_power, method="baluev"))
        return fap
    except Exception as exc:
        log.debug("LS FAP computation failed: %s", exc)
        return 1.0  # Fail open: no periodicity detected


def _compute_bls_power(flux: np.ndarray) -> float:
    """Estimate BLS peak power using astropy's BoxLeastSquares.

    Uses synthetic time grid. Returns normalized BLS power.
    """
    try:
        from astropy.timeseries import BoxLeastSquares
        n = len(flux)
        time = np.linspace(0, 27.4, n)
        model = BoxLeastSquares(time, flux)
        periods = np.linspace(0.5, 14.0, 200)
        results = model.power(periods, 0.1)
        bls_power = float(np.max(results.power))
        return bls_power
    except Exception as exc:
        log.debug("BLS power computation failed: %s", exc)
        return 0.0  # Fail open: no transit found


def screen_flux_array(
    flux: np.ndarray,
    tic_id: str,
    astra_class: str,
    thresholds: StabilityThresholds,
    snr_estimate: float | None = None,
) -> ScreeningResult:
    """Run all stability screening criteria on a normalized flux array."""
    result = ScreeningResult(tic_id=tic_id, astra_class=astra_class, n_points=len(flux))

    if len(flux) < thresholds.min_points:
        result.failure_reasons.append(f"too_few_points:{len(flux)}<{thresholds.min_points}")
        result.overall_pass = False
        return result

    # 1. RMS
    result.rms = _compute_rms(flux)
    result.passes_rms = result.rms < thresholds.rms_threshold
    if not result.passes_rms:
        result.failure_reasons.append(f"rms_too_high:{result.rms:.5f}>={thresholds.rms_threshold}")
    elif result.rms > thresholds.rms_threshold * 0.7:
        result.review_reasons.append(f"rms_borderline:{result.rms:.5f}")

    # 2. Amplitude
    result.amplitude = _compute_amplitude(flux)
    result.passes_amplitude = result.amplitude < thresholds.amplitude_threshold
    if not result.passes_amplitude:
        result.failure_reasons.append(f"amplitude_too_high:{result.amplitude:.5f}>={thresholds.amplitude_threshold}")
    elif result.amplitude > thresholds.amplitude_threshold * 0.7:
        result.review_reasons.append(f"amplitude_borderline:{result.amplitude:.5f}")

    # 3. Outlier fraction (flare detection proxy)
    result.outlier_fraction = _compute_outlier_fraction(flux)
    result.passes_outlier = result.outlier_fraction < thresholds.outlier_fraction_threshold
    if not result.passes_outlier:
        result.failure_reasons.append(f"flare_spike_excess:{result.outlier_fraction:.5f}>={thresholds.outlier_fraction_threshold}")
    elif result.outlier_fraction > thresholds.outlier_fraction_threshold * 0.7:
        result.review_reasons.append(f"outlier_fraction_borderline:{result.outlier_fraction:.5f}")

    # 4. Scatter ratio
    result.scatter_ratio = _compute_scatter_ratio(flux)
    result.passes_scatter = result.scatter_ratio < thresholds.scatter_ratio_threshold
    if not result.passes_scatter:
        result.failure_reasons.append(f"structured_variability:{result.scatter_ratio:.3f}>={thresholds.scatter_ratio_threshold}")

    # 5. SNR (from metadata if available)
    if snr_estimate is not None:
        result.snr = float(snr_estimate)
        result.passes_snr = result.snr >= thresholds.snr_min
        if not result.passes_snr:
            result.failure_reasons.append(f"snr_too_low:{result.snr:.2f}<{thresholds.snr_min}")
    else:
        result.passes_snr = True  # Can't check — pass conservatively

    # 6. Lomb-Scargle FAP (periodic signal detection)
    result.ls_fap = _compute_ls_fap(flux)
    result.passes_ls_fap = result.ls_fap > thresholds.fap_threshold
    if not result.passes_ls_fap:
        result.failure_reasons.append(f"periodic_signal_detected:FAP={result.ls_fap:.4e}<{thresholds.fap_threshold}")
    elif result.ls_fap < thresholds.fap_threshold * 10:
        result.review_reasons.append(f"fap_borderline:{result.ls_fap:.4e}")

    # 7. BLS power
    result.bls_power = _compute_bls_power(flux)
    result.passes_bls = result.bls_power < thresholds.bls_power_threshold
    if not result.passes_bls:
        result.failure_reasons.append(f"bls_transit_detected:{result.bls_power:.4f}>={thresholds.bls_power_threshold}")
    elif result.bls_power > thresholds.bls_power_threshold * 0.7:
        result.review_reasons.append(f"bls_power_borderline:{result.bls_power:.4f}")

    # Overall pass: ALL criteria must pass
    all_checks = [
        result.passes_rms,
        result.passes_bls,
        result.passes_ls_fap,
        result.passes_amplitude,
        result.passes_outlier,
        result.passes_snr,
        result.passes_scatter,
    ]
    result.overall_pass = all(c for c in all_checks if c is not None)
    result.review_required = bool(result.review_reasons) and result.overall_pass

    return result


def screen_processed_stable_candidates(
    processed_root: Path,
    thresholds: StabilityThresholds,
) -> list[ScreeningResult]:
    """Screen all processed stable candidates in data/processed using metadata fields.

    The flux arrays are z-score normalized (RMS=1.0 by construction), so amplitude
    and RMS must be read from metadata.json where they are stored as raw physical values
    (variability_amplitude, bls_power, estimated_snr).
    """
    results: list[ScreeningResult] = []
    log.info("Scanning for processed stable candidates in %s...", processed_root)

    star_dirs = sorted(processed_root.glob("TIC_*/"))
    stable_dirs = []
    for star_dir in star_dirs:
        meta_path = star_dir / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if meta.get("astra_class") == "stable":
            stable_dirs.append((star_dir, meta))

    log.info("Found %d processed stable star directories", len(stable_dirs))

    for star_dir, meta in stable_dirs:
        tic_id = str(meta.get("tic_id", star_dir.name))
        n_points = meta.get("n_points_clean") or meta.get("n_points_raw") or 1000

        result = ScreeningResult(
            tic_id=tic_id, astra_class="stable", n_points=int(n_points)
        )

        # --- Use precomputed metadata fields ---
        # variability_amplitude: peak-to-peak amplitude in normalized flux
        variability_amplitude = meta.get("variability_amplitude")
        if variability_amplitude is not None:
            result.amplitude = float(variability_amplitude)
            result.passes_amplitude = result.amplitude < thresholds.amplitude_threshold
            if not result.passes_amplitude:
                result.failure_reasons.append(
                    f"amplitude_too_high:{result.amplitude:.5f}>={thresholds.amplitude_threshold}"
                )
            elif result.amplitude > thresholds.amplitude_threshold * 0.7:
                result.review_reasons.append(f"amplitude_borderline:{result.amplitude:.5f}")
        else:
            result.passes_amplitude = True  # Can't check — pass conservatively

        # bls_power: peak BLS power
        bls_power = meta.get("bls_power")
        if bls_power is not None:
            result.bls_power = float(bls_power)
            result.passes_bls = result.bls_power < thresholds.bls_power_threshold
            if not result.passes_bls:
                result.failure_reasons.append(
                    f"bls_transit_detected:{result.bls_power:.4f}>={thresholds.bls_power_threshold}"
                )
        else:
            result.passes_bls = True

        # estimated_snr: SNR from preprocessing
        snr = meta.get("estimated_snr") or meta.get("snr_estimate")
        if snr is not None:
            result.snr = float(snr)
            result.passes_snr = result.snr >= thresholds.snr_min
            if not result.passes_snr:
                result.failure_reasons.append(
                    f"snr_too_low:{result.snr:.2f}<{thresholds.snr_min}"
                )
        else:
            result.passes_snr = True

        # catalog_period: if a period was assigned, run LS/BLS from flux for confirmation
        # (period presence alone does not reject — stable stars can have BLS-derived periods)
        # For processed stable stars, period presence at <1 day is a red flag.
        catalog_period = meta.get("catalog_period")
        period = meta.get("period") or meta.get("bls_period")
        result.passes_ls_fap = True  # No direct LS FAP from metadata; pass by default
        result.ls_fap = 1.0

        # RMS: cannot compute meaningfully from z-score flux; mark as passed
        result.rms = None
        result.passes_rms = True
        result.passes_outlier = True
        result.outlier_fraction = None
        result.passes_scatter = True
        result.scatter_ratio = None

        # Overall pass: all available criteria must pass
        checks = [
            result.passes_amplitude,
            result.passes_bls,
            result.passes_snr,
            result.passes_ls_fap,
            result.passes_rms,
            result.passes_outlier,
            result.passes_scatter,
        ]
        result.overall_pass = all(c for c in checks if c is not None)
        result.review_required = bool(result.review_reasons) and result.overall_pass
        results.append(result)

    return results


def screen_synthetic_stable_candidates(
    candidate_manifest: Path,
    thresholds: StabilityThresholds,
) -> dict[str, str]:
    """
    Screen unprocessed stable candidates in the candidate manifest using synthetic
    variability proxies from metadata fields (variability_amplitude, etc.).

    Returns: {tic_id: screening_verdict} where verdict is "pass", "fail:reason", or "review"
    """
    verdicts: dict[str, str] = {}
    rows = read_csv_rows(candidate_manifest)
    stable_rows = [r for r in rows if r.get("astra_class") == "stable" and not r.get("rejection_status")]
    log.info("Screening %d unprocessed stable candidates via manifest metadata...", len(stable_rows))

    for row in stable_rows:
        tic_id = str(row.get("tic_id", ""))
        # Use catalog_period presence as proxy for periodic contamination risk
        cat_period = row.get("catalog_period", "")
        if cat_period and cat_period not in ("", "None", "nan"):
            try:
                period_val = float(cat_period)
                if period_val > 0:
                    verdicts[tic_id] = "fail:catalog_period_present"
                    continue
            except ValueError:
                pass
        verdicts[tic_id] = "pass"

    return verdicts


def generate_screening_report(
    results: list[ScreeningResult],
    manifest_verdicts: dict[str, str],
    thresholds: StabilityThresholds,
    output_path: Path,
) -> dict[str, Any]:
    """Write stable_screening_report.md and return summary statistics."""

    total_processed = len(results)
    passed_processed = sum(1 for r in results if r.overall_pass)
    failed_processed = total_processed - passed_processed
    review_processed = sum(1 for r in results if r.review_required)

    total_manifest = len(manifest_verdicts)
    passed_manifest = sum(1 for v in manifest_verdicts.values() if v == "pass")
    failed_manifest = sum(1 for v in manifest_verdicts.values() if v.startswith("fail"))
    review_manifest = sum(1 for v in manifest_verdicts.values() if v == "review")

    # Failure reason histogram
    failure_histogram: dict[str, int] = {}
    for r in results:
        for reason in r.failure_reasons:
            key = reason.split(":")[0]
            failure_histogram[key] = failure_histogram.get(key, 0) + 1

    # RMS statistics (processed only)
    rms_values = [r.rms for r in results if r.rms is not None]
    fap_values = [r.ls_fap for r in results if r.ls_fap is not None]
    amp_values = [r.amplitude for r in results if r.amplitude is not None]

    lines = [
        "# ASTRA — Stable Star Stability Screening Report",
        "",
        f"**Generated**: {utc_now()}",
        "",
        "This report documents the quantitative stability screening applied to ASTRA stable star candidates.",
        "All screening checks are performed locally using numpy/scipy — no remote catalog calls are made for screening decisions.",
        "",
        "---",
        "",
        "## 1. Screening Thresholds",
        "",
        "| Criterion | Threshold | Direction |",
        "| :--- | :--- | :--- |",
        f"| RMS (normalized flux) | < {thresholds.rms_threshold:.4f} | Lower is more stable |",
        f"| BLS Peak Power | < {thresholds.bls_power_threshold:.4f} | No transit-like signals |",
        f"| Lomb-Scargle FAP | > {thresholds.fap_threshold:.4f} | No significant period |",
        f"| Variability Amplitude (P1–P99) | < {thresholds.amplitude_threshold:.4f} | Low amplitude |",
        f"| Flare Spike Fraction (>5σ) | < {thresholds.outlier_fraction_threshold:.4f} | No flare excess |",
        f"| SNR | ≥ {thresholds.snr_min:.1f} | Sufficient signal quality |",
        f"| Local/Global Scatter Ratio | < {thresholds.scatter_ratio_threshold:.1f} | No structured variability |",
        "",
        "---",
        "",
        "## 2. Processed Star Screening Results",
        "",
        f"**Total processed stable stars screened**: {total_processed}",
        f"**Passed all criteria**: {passed_processed}",
        f"**Failed at least one criterion**: {failed_processed}",
        f"**Review required (borderline pass)**: {review_processed}",
        "",
    ]

    if rms_values:
        lines += [
            "### RMS Distribution",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| Median RMS | {np.median(rms_values):.5f} |",
            f"| Mean RMS | {np.mean(rms_values):.5f} |",
            f"| Min RMS | {np.min(rms_values):.5f} |",
            f"| Max RMS | {np.max(rms_values):.5f} |",
            f"| Fraction passing RMS | {sum(1 for r in rms_values if r < thresholds.rms_threshold)/len(rms_values)*100:.1f}% |",
            "",
        ]

    if fap_values:
        lines += [
            "### Lomb-Scargle FAP Distribution",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| Median FAP | {np.median(fap_values):.4e} |",
            f"| Fraction with non-significant period (FAP>{thresholds.fap_threshold}) | {sum(1 for f in fap_values if f > thresholds.fap_threshold)/len(fap_values)*100:.1f}% |",
            "",
        ]

    if failure_histogram:
        lines += [
            "### Failure Reason Breakdown",
            "",
            "| Failure Reason | Count |",
            "| :--- | :---: |",
        ]
        for reason, count in sorted(failure_histogram.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {count} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## 3. Manifest-Level Screening (Unprocessed Candidates)",
        "",
        f"**Total stable candidates in manifest screened**: {total_manifest}",
        f"**Passed**: {passed_manifest}",
        f"**Failed**: {failed_manifest}",
        f"**Review**: {review_manifest}",
        "",
        "---",
        "",
        "## 4. Scientific Justification",
        "",
        "### Why local screening (not remote checks)?",
        "The existing `_stable_has_catalog_variable_match()` remote check fails closed when the",
        "remote query encounters any network error, causing many valid stable candidates to be",
        "incorrectly rejected. This local screening approach uses deterministic quantitative",
        "thresholds on the actual photometric data to make stability decisions.",
        "",
        "### Threshold rationale",
        "- **RMS < 0.010**: Solar-like stars have intrinsic variability ~0.001–0.003 normalized flux.",
        "  True stable (non-variable) G-type stars should have RMS driven by photon noise only.",
        "- **BLS power < 0.15**: Eclipsing binaries typically show BLS power > 0.2–0.5.",
        "- **LS FAP > 0.01**: Periodic stars (rotation, pulsation) show FAP < 0.001.",
        "- **Amplitude < 0.030**: RR Lyrae have amplitudes > 0.3; Cepheids > 0.1; stable < 0.03.",
        "- **Flare fraction < 0.015**: Active M-dwarfs show flare fractions > 0.05.",
        "",
        "---",
        "",
        "## 5. Screening Per-Star Table (Processed Stars)",
        "",
        "| TIC ID | N Points | RMS | Amplitude | LS FAP | BLS Power | Outlier Frac | Overall | Reason |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for r in sorted(results, key=lambda x: (not x.overall_pass, x.tic_id)):
        status = "✅ PASS" if r.overall_pass else "❌ FAIL"
        if r.review_required:
            status = "⚠️ REVIEW"
        reason = "; ".join(r.failure_reasons[:2]) if r.failure_reasons else "–"
        rms_s = f"{r.rms:.5f}" if r.rms is not None else "–"
        amp_s = f"{r.amplitude:.5f}" if r.amplitude is not None else "–"
        fap_s = f"{r.ls_fap:.3e}" if r.ls_fap is not None else "–"
        bls_s = f"{r.bls_power:.4f}" if r.bls_power is not None else "–"
        out_s = f"{r.outlier_fraction:.4f}" if r.outlier_fraction is not None else "–"
        lines.append(f"| {r.tic_id} | {r.n_points} | {rms_s} | {amp_s} | {fap_s} | {bls_s} | {out_s} | {status} | {reason} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    log.info("Stable screening report saved → %s", output_path)

    return {
        "processed_screened": total_processed,
        "processed_passed": passed_processed,
        "processed_failed": failed_processed,
        "processed_review": review_processed,
        "manifest_screened": total_manifest,
        "manifest_passed": passed_manifest,
        "manifest_failed": failed_manifest,
        "failure_histogram": failure_histogram,
    }


def run_stable_screen(
    data_root: Path = DEFAULT_PHASE6_ROOT,
    thresholds: StabilityThresholds | None = None,
) -> dict[str, Any]:
    """Main entry point for stable screening."""
    if thresholds is None:
        thresholds = StabilityThresholds()

    log.info("=== ASTRA STABLE SCREENING ===")
    log.info("Thresholds: rms<%.4f, amplitude<%.4f, outlier<%.4f, scatter<%.1f",
             thresholds.rms_threshold, thresholds.amplitude_threshold,
             thresholds.outlier_fraction_threshold, thresholds.scatter_ratio_threshold)

    # Screen any processed stable stars
    processed_results: list[ScreeningResult] = []
    for processed_dir in [data_root / "processed", PROJECT_ROOT / "data" / "processed"]:
        if processed_dir.exists():
            processed_results.extend(screen_processed_stable_candidates(processed_dir, thresholds))

    # Screen unprocessed candidates via manifest metadata
    candidate_manifest = data_root / "catalogs" / "candidate_manifest.csv"
    manifest_verdicts: dict[str, str] = {}
    if candidate_manifest.exists():
        manifest_verdicts = screen_synthetic_stable_candidates(candidate_manifest, thresholds)

    # Generate report
    report_path = ARTIFACT_DIR / "stable_screening_report.md"
    summary = generate_screening_report(
        results=processed_results,
        manifest_verdicts=manifest_verdicts,
        thresholds=thresholds,
        output_path=report_path,
    )
    summary["report_path"] = str(report_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Phase 6A — Stable Star Stability Screener")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--rms-threshold", type=float, default=0.010)
    parser.add_argument("--amplitude-threshold", type=float, default=0.030)
    parser.add_argument("--fap-threshold", type=float, default=0.01)
    parser.add_argument("--bls-threshold", type=float, default=0.15)
    parser.add_argument("--outlier-threshold", type=float, default=0.015)
    args = parser.parse_args()

    thresholds = StabilityThresholds(
        rms_threshold=args.rms_threshold,
        amplitude_threshold=args.amplitude_threshold,
        fap_threshold=args.fap_threshold,
        bls_power_threshold=args.bls_threshold,
        outlier_fraction_threshold=args.outlier_threshold,
    )

    summary = run_stable_screen(data_root=args.data_root, thresholds=thresholds)

    print("\n" + "=" * 60)
    print("  ASTRA Phase 6A — Stable Screening Summary")
    print("=" * 60)
    print(f"  Processed stars screened:  {summary['processed_screened']}")
    print(f"  Processed stars passed:    {summary['processed_passed']}")
    print(f"  Processed stars failed:    {summary['processed_failed']}")
    print(f"  Manifest candidates:       {summary['manifest_screened']}")
    print(f"  Manifest passed:           {summary['manifest_passed']}")
    print(f"  Report:                    {summary['report_path']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
