#!/usr/bin/env python3
"""
ASTRA Phase 6A — variability_crosscheck.py

Cross-reference solar_like and stable candidates against published variable star catalogs
to detect contamination WITHOUT blocking on network failures (fail-open for acquisition,
but report all contamination findings for manual review).

Catalogs queried:
  1. VSX (B/vsx/vsx) — AAVSO Variable Star Index
  2. Gaia DR3 variability class (I/358/vclassre)
  3. ASAS-SN variable stars (II/366/catalog)
  4. OGLE variable stars (J/AcA/62/219) — if accessible

Outputs:
  - contamination_audit.md (human-readable report)
  - contamination_detail.csv (machine-readable per-star results)

Contamination classification:
  CONFIRMED   — star appears in a variable catalog with a classifiable variable type
  SUSPECTED   — star appears in a catalog but type is ambiguous or unclassified
  BORDERLINE  — star is within 10–20 arcsec of a variable; may be blend
  CLEAN       — no match within 20 arcsec in any checked catalog

Usage:
    python pipeline/variability_crosscheck.py
    python pipeline/variability_crosscheck.py --radius 10.0
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES
from pipeline.phase6_utils import (
    DEFAULT_PHASE6_ROOT,
    angular_separation_arcsec,
    read_csv_rows,
    utc_now,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("variability_crosscheck")

ARTIFACT_DIR = Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/6213b34b-7bbc-4ddd-bf18-dae93ae7cb54")

# VSX types that clearly indicate contamination for solar_like/stable
DEFINITE_VARIABLE_TYPES = {
    "RRAB", "RRC", "RRD", "RR",
    "DCEP", "DCEPS", "CEP", "CW", "CWA", "CWB",
    "EA", "EB", "EW", "EP",
    "M", "SR", "SRB", "SRS", "SRA", "SRD",
    "L", "LB", "LC", "LPV",
    "DSCT", "HADS", "SX",
    "BY", "RS", "FLARE",
    "W",  # W UMa
    "ELL",  # Ellipsoidal
    "RPHS", "ZZ",
}

AMBIGUOUS_VARIABLE_TYPES = {"VAR", "ROT", "INT", "MISC", ""}

# VSX types that explicitly mean "constant" / "not variable" — should NOT flag contamination
CONSTANT_VSX_TYPES = {"CST", "CONST", "CONSTANT", "ORG"}  # ORG = organizational entry, not a variability type


@dataclass
class CrosscheckResult:
    """Contamination crosscheck result for a single star."""
    tic_id: str
    name: str
    astra_class: str
    ra: float
    dec: float
    # Contamination findings per catalog
    vsx_match_type: str = ""
    vsx_match_sep_arcsec: float = -1.0
    gaia_match_type: str = ""
    gaia_match_sep_arcsec: float = -1.0
    asas_match_type: str = ""
    asas_match_sep_arcsec: float = -1.0
    # Classification
    contamination_status: str = "CLEAN"   # CONFIRMED | SUSPECTED | BORDERLINE | CLEAN
    contamination_reason: str = ""
    catalogs_checked: list[str] = field(default_factory=list)
    catalog_failures: list[str] = field(default_factory=list)
    check_timestamp: str = ""


def _classify_contamination(match_type: str, sep: float) -> str:
    """Classify contamination level from a catalog match."""
    type_upper = match_type.upper().strip()

    # Explicit constant-star designations are NOT contamination
    if type_upper in CONSTANT_VSX_TYPES:
        return "CLEAN"

    if not type_upper:
        if sep <= 10.0:
            return "SUSPECTED"
        elif sep <= 20.0:
            return "BORDERLINE"
        return "CLEAN"
    # Check for definite variable types
    for vtype in DEFINITE_VARIABLE_TYPES:
        if type_upper.startswith(vtype):
            return "CONFIRMED"
    # Ambiguous types at close separation
    if sep <= 5.0:
        return "SUSPECTED"
    if sep <= 20.0:
        return "BORDERLINE"
    return "CLEAN"


def _query_vsx_single(ra: float, dec: float, radius_arcsec: float = 20.0) -> tuple[str, float, bool]:
    """Query VSX catalog for a single position. Returns (type, sep_arcsec, query_ok)."""
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier

        coord = SkyCoord(ra=ra, dec=dec, unit="deg")
        viz = Vizier(columns=["OID", "Type", "RAJ2000", "DEJ2000"], row_limit=5)
        tables = viz.query_region(coord, radius=radius_arcsec * u.arcsec, catalog="B/vsx/vsx")
        if not tables or len(tables) == 0 or len(tables[0]) == 0:
            return "", -1.0, True
        row = tables[0][0]
        try:
            match_ra = float(row["RAJ2000"])
            match_dec = float(row["DEJ2000"])
            sep = angular_separation_arcsec(ra, dec, match_ra, match_dec)
        except Exception:
            sep = 0.0
        vsx_type = str(row.get("Type", "") or "")
        return vsx_type, sep, True
    except Exception:
        return "", -1.0, False


def _query_gaia_variable_single(ra: float, dec: float, radius_arcsec: float = 20.0) -> tuple[str, float, bool]:
    """Query Gaia DR3 variability catalog for a single position."""
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier

        coord = SkyCoord(ra=ra, dec=dec, unit="deg")
        viz = Vizier(columns=["**"], row_limit=5)
        tables = viz.query_region(coord, radius=radius_arcsec * u.arcsec, catalog="I/358/vclassre")
        if not tables or len(tables) == 0 or len(tables[0]) == 0:
            return "", -1.0, True
        row = tables[0][0]
        col_lower = {c.lower(): c for c in tables[0].colnames}
        class_col = col_lower.get("best_class_name") or col_lower.get("class")
        gaia_type = str(row[class_col]) if class_col else ""
        ra_col = col_lower.get("raj2000") or col_lower.get("ra") or col_lower.get("raicrs")
        dec_col = col_lower.get("dej2000") or col_lower.get("dec") or col_lower.get("deicrs")
        sep = 0.0
        if ra_col and dec_col:
            try:
                sep = angular_separation_arcsec(ra, dec, float(row[col_lower[ra_col]]), float(row[col_lower[dec_col]]))
            except Exception:
                pass
        return gaia_type, sep, True
    except Exception:
        return "", -1.0, False


def _query_asas_single(ra: float, dec: float, radius_arcsec: float = 20.0) -> tuple[str, float, bool]:
    """Query ASAS-SN variable catalog for a single position."""
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier

        coord = SkyCoord(ra=ra, dec=dec, unit="deg")
        viz = Vizier(columns=["**"], row_limit=5)
        tables = viz.query_region(coord, radius=radius_arcsec * u.arcsec, catalog="II/366/catalog")
        if not tables or len(tables) == 0 or len(tables[0]) == 0:
            return "", -1.0, True
        row = tables[0][0]
        col_lower = {c.lower(): c for c in tables[0].colnames}
        type_col = col_lower.get("type") or col_lower.get("vartype")
        asas_type = str(row[col_lower[type_col]]) if type_col else ""
        ra_col = col_lower.get("raj2000") or col_lower.get("ra")
        dec_col = col_lower.get("dej2000") or col_lower.get("dec")
        sep = 0.0
        if ra_col and dec_col:
            try:
                sep = angular_separation_arcsec(ra, dec, float(row[col_lower[ra_col]]), float(row[col_lower[dec_col]]))
            except Exception:
                pass
        return asas_type, sep, True
    except Exception:
        return "", -1.0, False


def crosscheck_candidate(
    row: dict,
    radius_arcsec: float = 20.0,
    retry_delay: float = 1.0,
) -> CrosscheckResult:
    """Run contamination crosscheck for a single candidate row."""
    tic_id = str(row.get("tic_id", ""))
    name = str(row.get("name", f"TIC {tic_id}"))
    astra_class = str(row.get("astra_class", ""))

    try:
        ra = float(row.get("ra", 0.0))
        dec = float(row.get("dec", 0.0))
    except (TypeError, ValueError):
        result = CrosscheckResult(
            tic_id=tic_id, name=name, astra_class=astra_class, ra=0, dec=0,
            contamination_status="CLEAN",
            contamination_reason="no_coordinates",
            check_timestamp=utc_now(),
        )
        result.catalog_failures.append("no_coordinates")
        return result

    result = CrosscheckResult(
        tic_id=tic_id, name=name, astra_class=astra_class, ra=ra, dec=dec,
        check_timestamp=utc_now(),
    )

    worst_contamination = "CLEAN"

    # Check VSX
    try:
        vsx_type, vsx_sep, vsx_ok = _query_vsx_single(ra, dec, radius_arcsec)
        if vsx_ok:
            result.catalogs_checked.append("VSX")
            result.vsx_match_type = vsx_type
            result.vsx_match_sep_arcsec = vsx_sep
            level = _classify_contamination(vsx_type, vsx_sep) if vsx_sep >= 0 else "CLEAN"
            if level != "CLEAN":
                worst_contamination = level if level == "CONFIRMED" else (
                    "CONFIRMED" if worst_contamination == "CONFIRMED" else level
                )
                result.contamination_reason += f"VSX:{vsx_type}@{vsx_sep:.1f}\" "
        else:
            result.catalog_failures.append("VSX_query_failed")
    except Exception as exc:
        result.catalog_failures.append(f"VSX_exception:{exc}")

    time.sleep(retry_delay * 0.5)

    # Check Gaia variability
    try:
        gaia_type, gaia_sep, gaia_ok = _query_gaia_variable_single(ra, dec, radius_arcsec)
        if gaia_ok:
            result.catalogs_checked.append("Gaia_DR3_var")
            result.gaia_match_type = gaia_type
            result.gaia_match_sep_arcsec = gaia_sep
            level = _classify_contamination(gaia_type, gaia_sep) if gaia_sep >= 0 else "CLEAN"
            if level != "CLEAN":
                if worst_contamination != "CONFIRMED":
                    worst_contamination = level
                result.contamination_reason += f"Gaia:{gaia_type}@{gaia_sep:.1f}\" "
        else:
            result.catalog_failures.append("Gaia_query_failed")
    except Exception as exc:
        result.catalog_failures.append(f"Gaia_exception:{exc}")

    time.sleep(retry_delay * 0.5)

    # Check ASAS-SN
    try:
        asas_type, asas_sep, asas_ok = _query_asas_single(ra, dec, radius_arcsec)
        if asas_ok:
            result.catalogs_checked.append("ASAS-SN")
            result.asas_match_type = asas_type
            result.asas_match_sep_arcsec = asas_sep
            level = _classify_contamination(asas_type, asas_sep) if asas_sep >= 0 else "CLEAN"
            if level != "CLEAN":
                if worst_contamination != "CONFIRMED":
                    worst_contamination = level
                result.contamination_reason += f"ASAS:{asas_type}@{asas_sep:.1f}\" "
        else:
            result.catalog_failures.append("ASAS_query_failed")
    except Exception as exc:
        result.catalog_failures.append(f"ASAS_exception:{exc}")

    result.contamination_status = worst_contamination
    result.contamination_reason = result.contamination_reason.strip()
    return result


def run_crosscheck(
    data_root: Path = DEFAULT_PHASE6_ROOT,
    classes_to_check: list[str] | None = None,
    radius_arcsec: float = 20.0,
    max_stars: int | None = None,
    batch_delay: float = 1.0,
) -> dict[str, Any]:
    """
    Run contamination crosscheck for solar_like and stable candidates.
    Returns summary statistics.
    """
    if classes_to_check is None:
        classes_to_check = ["solar_like", "stable"]

    candidate_manifest = data_root / "catalogs" / "candidate_manifest.csv"
    if not candidate_manifest.exists():
        log.error("Candidate manifest not found: %s", candidate_manifest)
        return {"error": "no_manifest"}

    all_rows = read_csv_rows(candidate_manifest)
    target_rows = [
        r for r in all_rows
        if r.get("astra_class") in classes_to_check
        and not r.get("rejection_status")
    ]

    if max_stars is not None:
        target_rows = target_rows[:max_stars]

    log.info("=== VARIABILITY CROSSCHECK ===")
    log.info("Target classes: %s", classes_to_check)
    log.info("Stars to check: %d (radius=%.1f\")", len(target_rows), radius_arcsec)

    results: list[CrosscheckResult] = []
    for i, row in enumerate(target_rows):
        tic_id = row.get("tic_id", "unknown")
        astra_class = row.get("astra_class", "")
        log.info("[%d/%d] Checking TIC %s (%s)...", i + 1, len(target_rows), tic_id, astra_class)
        result = crosscheck_candidate(row, radius_arcsec=radius_arcsec, retry_delay=batch_delay)
        results.append(result)
        if (i + 1) % 10 == 0:
            time.sleep(batch_delay)

    # Generate reports
    summary = _generate_contamination_report(results, radius_arcsec)
    return summary


def _generate_contamination_report(
    results: list[CrosscheckResult],
    radius_arcsec: float,
) -> dict[str, Any]:
    """Write contamination_audit.md and contamination_detail.csv."""

    # Statistics
    by_class: dict[str, dict[str, int]] = {}
    for r in results:
        cls = r.astra_class
        if cls not in by_class:
            by_class[cls] = {"CLEAN": 0, "BORDERLINE": 0, "SUSPECTED": 0, "CONFIRMED": 0, "total": 0}
        by_class[cls][r.contamination_status] = by_class[cls].get(r.contamination_status, 0) + 1
        by_class[cls]["total"] += 1

    total_clean = sum(1 for r in results if r.contamination_status == "CLEAN")
    total_confirmed = sum(1 for r in results if r.contamination_status == "CONFIRMED")
    total_suspected = sum(1 for r in results if r.contamination_status == "SUSPECTED")
    total_borderline = sum(1 for r in results if r.contamination_status == "BORDERLINE")
    total_failures = sum(1 for r in results if r.catalog_failures)

    # Write contamination_audit.md
    audit_path = ARTIFACT_DIR / "contamination_audit.md"
    lines = [
        "# ASTRA — Variability Contamination Audit",
        "",
        f"**Generated**: {utc_now()}",
        f"**Search radius**: {radius_arcsec:.1f} arcsec",
        "**Catalogs consulted**: VSX (AAVSO), Gaia DR3 variability, ASAS-SN",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Count |",
        "| :--- | :---: |",
        f"| Total stars checked | {len(results)} |",
        f"| CLEAN (no variable catalog match) | {total_clean} |",
        f"| BORDERLINE (10–20\" from variable) | {total_borderline} |",
        f"| SUSPECTED (close match, ambiguous type) | {total_suspected} |",
        f"| CONFIRMED CONTAMINATION | {total_confirmed} |",
        f"| Catalog query failures | {total_failures} |",
        "",
        "> [!NOTE]",
        "> CONFIRMED contamination candidates should be removed from the usable manifest.",
        "> SUSPECTED and BORDERLINE candidates require human review.",
        "> Stars with catalog query failures are treated as CLEAN (fail-open) for acquisition.",
        "",
        "---",
        "",
        "## 2. Contamination by Class",
        "",
        "| Class | Total | CLEAN | BORDERLINE | SUSPECTED | CONFIRMED |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cls, counts in by_class.items():
        lines.append(
            f"| {cls} | {counts['total']} | {counts.get('CLEAN', 0)} | "
            f"{counts.get('BORDERLINE', 0)} | {counts.get('SUSPECTED', 0)} | "
            f"{counts.get('CONFIRMED', 0)} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Contamination Rate Assessment",
        "",
    ]

    for cls, counts in by_class.items():
        total = counts["total"]
        if total == 0:
            continue
        clean_pct = counts.get("CLEAN", 0) / total * 100
        confirmed_pct = counts.get("CONFIRMED", 0) / total * 100
        status = "✅ ACCEPTABLE" if confirmed_pct < 5.0 else "⚠️ HIGH" if confirmed_pct < 15.0 else "❌ CRITICAL"
        lines += [
            f"### {cls}",
            f"- Clean rate: **{clean_pct:.1f}%**",
            f"- Contamination rate: **{confirmed_pct:.1f}%** — {status}",
            f"- Recommended action: {'Accept for acquisition' if confirmed_pct < 5.0 else 'Reject CONFIRMED, review SUSPECTED'}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 4. Confirmed Contaminated Stars",
        "",
        "| TIC ID | Name | Class | VSX Type | Gaia Type | ASAS Type | Sep (\") | Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    confirmed = [r for r in results if r.contamination_status == "CONFIRMED"]
    for r in sorted(confirmed, key=lambda x: x.astra_class):
        vsx_s = f"{r.vsx_match_type}" if r.vsx_match_sep_arcsec >= 0 else "–"
        gaia_s = f"{r.gaia_match_type}" if r.gaia_match_sep_arcsec >= 0 else "–"
        asas_s = f"{r.asas_match_type}" if r.asas_match_sep_arcsec >= 0 else "–"
        sep_s = f"{max(r.vsx_match_sep_arcsec, r.gaia_match_sep_arcsec, r.asas_match_sep_arcsec):.1f}"
        lines.append(f"| {r.tic_id} | {r.name} | {r.astra_class} | {vsx_s} | {gaia_s} | {asas_s} | {sep_s} | {r.contamination_reason} |")

    if not confirmed:
        lines.append("| *None* | | | | | | | |")

    lines += [
        "",
        "---",
        "",
        "## 5. Stars Requiring Review (SUSPECTED + BORDERLINE)",
        "",
        "| TIC ID | Name | Class | Status | Catalogs | Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    review = [r for r in results if r.contamination_status in ("SUSPECTED", "BORDERLINE")]
    for r in sorted(review, key=lambda x: (x.astra_class, x.contamination_status)):
        catalogs = ", ".join(r.catalogs_checked)
        lines.append(f"| {r.tic_id} | {r.name} | {r.astra_class} | {r.contamination_status} | {catalogs} | {r.contamination_reason} |")

    if not review:
        lines.append("| *None* | | | | | |")

    lines += [
        "",
        "---",
        "",
        "## 6. Catalog Query Failures",
        "",
        "Stars below had query failures. They are treated as CLEAN (fail-open) for acquisition,",
        "but should be reviewed manually if they appear in the usable manifest.",
        "",
        "| TIC ID | Name | Class | Failed Catalogs |",
        "| :--- | :--- | :--- | :--- |",
    ]

    failures = [r for r in results if r.catalog_failures]
    for r in failures[:50]:  # Cap to 50 to avoid huge tables
        fail_str = "; ".join(r.catalog_failures[:3])
        lines.append(f"| {r.tic_id} | {r.name} | {r.astra_class} | {fail_str} |")

    if len(failures) > 50:
        lines.append(f"| ... | *{len(failures) - 50} more* | | |")

    if not failures:
        lines.append("| *None* | | | |")

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("\n".join(lines) + "\n")
    log.info("Contamination audit → %s", audit_path)

    # Write per-star CSV
    detail_path = ARTIFACT_DIR / "contamination_detail.csv"
    fieldnames = [
        "tic_id", "name", "astra_class", "ra", "dec",
        "vsx_match_type", "vsx_match_sep_arcsec",
        "gaia_match_type", "gaia_match_sep_arcsec",
        "asas_match_type", "asas_match_sep_arcsec",
        "contamination_status", "contamination_reason",
        "catalogs_checked", "catalog_failures", "check_timestamp",
    ]
    with open(detail_path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "tic_id": r.tic_id,
                "name": r.name,
                "astra_class": r.astra_class,
                "ra": r.ra,
                "dec": r.dec,
                "vsx_match_type": r.vsx_match_type,
                "vsx_match_sep_arcsec": r.vsx_match_sep_arcsec,
                "gaia_match_type": r.gaia_match_type,
                "gaia_match_sep_arcsec": r.gaia_match_sep_arcsec,
                "asas_match_type": r.asas_match_type,
                "asas_match_sep_arcsec": r.asas_match_sep_arcsec,
                "contamination_status": r.contamination_status,
                "contamination_reason": r.contamination_reason,
                "catalogs_checked": json.dumps(r.catalogs_checked),
                "catalog_failures": json.dumps(r.catalog_failures),
                "check_timestamp": r.check_timestamp,
            })
    log.info("Contamination detail CSV → %s", detail_path)

    return {
        "total_checked": len(results),
        "total_clean": total_clean,
        "total_borderline": total_borderline,
        "total_suspected": total_suspected,
        "total_confirmed": total_confirmed,
        "total_failures": total_failures,
        "by_class": by_class,
        "audit_path": str(audit_path),
        "detail_path": str(detail_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Phase 6A — Variability Crosscheck")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--radius", type=float, default=20.0, help="Search radius in arcseconds")
    parser.add_argument("--max-stars", type=int, default=None, help="Maximum stars to check (for testing)")
    parser.add_argument("--classes", nargs="+", default=["solar_like", "stable"],
                        choices=list(CLASS_NAMES), help="Classes to crosscheck")
    parser.add_argument("--batch-delay", type=float, default=1.0, help="Delay between batch queries (s)")
    args = parser.parse_args()

    summary = run_crosscheck(
        data_root=args.data_root,
        classes_to_check=args.classes,
        radius_arcsec=args.radius,
        max_stars=args.max_stars,
        batch_delay=args.batch_delay,
    )

    print("\n" + "=" * 60)
    print("  ASTRA Phase 6A — Variability Crosscheck Summary")
    print("=" * 60)
    print(f"  Total stars checked:   {summary.get('total_checked', 0)}")
    print(f"  CLEAN:                 {summary.get('total_clean', 0)}")
    print(f"  BORDERLINE:            {summary.get('total_borderline', 0)}")
    print(f"  SUSPECTED:             {summary.get('total_suspected', 0)}")
    print(f"  CONFIRMED contaminated:{summary.get('total_confirmed', 0)}")
    print(f"  Query failures:        {summary.get('total_failures', 0)}")
    print(f"  Report:                {summary.get('audit_path', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
