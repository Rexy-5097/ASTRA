#!/usr/bin/env python3
"""Build Phase 6 catalog manifests for ASTRA.

This script builds candidate, resolved, and usable manifests. It does not
download light curves. Rows only become usable after TESS availability is
verified and the label source passes strict checks.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import socket
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES
from pipeline.phase6_utils import (
    DEFAULT_PHASE6_ROOT,
    MANIFEST_COLUMNS,
    REJECTED_COLUMNS,
    angular_separation_arcsec,
    append_csv_row,
    assign_duplicate_groups,
    ensure_phase6_structure,
    normalize_tic_id,
    read_csv_rows,
    utc_now,
    write_csv_rows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dataset_builder")
socket.setdefaulttimeout(45)

LEGACY_CATALOG = PROJECT_ROOT / "data" / "catalog_full.json"
VARIABLE_CLASSES = {"rr_lyrae", "cepheid", "eclipsing_binary"}
VARIABLE_SOURCE_NAMES = {"VSX", "Gaia", "ASAS-SN", "OGLE"}


def _load_legacy_catalog(limit_per_class: int | None = None) -> list[dict[str, Any]]:
    if not LEGACY_CATALOG.exists():
        return []

    rows = json.loads(LEGACY_CATALOG.read_text())
    counts: dict[str, int] = defaultdict(int)
    out: list[dict[str, Any]] = []
    for row in rows:
        cls = row.get("astra_class")
        if cls not in CLASS_NAMES:
            continue
        if limit_per_class is not None and counts[cls] >= limit_per_class:
            continue
        counts[cls] += 1
        out.append(_candidate_from_source(row, row.get("source", "legacy_catalog")))
    return out


def _query_catalog_sources(target_per_class: int) -> list[dict[str, Any]]:
    """Use the current catalog builders as source adapters.

    This keeps Phase 6 aligned with the existing project while adding strict
    manifests and duplicate control.
    """
    from pipeline.build_catalog import _build_solar_like, _build_stable, _query_vsx_class

    rows: list[dict[str, Any]] = []
    for cls in ("rr_lyrae", "cepheid", "eclipsing_binary"):
        for row in _query_vsx_class(cls, target_per_class):
            rows.append(_candidate_from_source(row, "VSX"))

    solar_rows = _build_solar_like(target_per_class)
    for row in solar_rows:
        rows.append(_candidate_from_source(row, row.get("source", "literature")))

    exclude_tics = {
        int(row["tic_id"])
        for row in solar_rows
        if row.get("tic_id") not in (None, "")
    }
    for row in _build_stable(target_per_class, exclude_tics):
        rows.append(_candidate_from_source(row, row.get("source", "stable_catalog")))
    return rows


def _query_gaia_variability(target_per_class: int) -> list[dict[str, Any]]:
    """Query Gaia variability classes from VizieR when available."""
    from astroquery.vizier import Vizier

    rows: list[dict[str, Any]] = []
    class_map = {
        "RR": "rr_lyrae",
        "CEP": "cepheid",
        "ECL": "eclipsing_binary",
    }
    try:
        viz = Vizier(columns=["**"], row_limit=target_per_class * 6)
        tables = viz.get_catalogs("I/358/vclassre")
    except Exception as exc:
        log.warning("Gaia variability adapter failed: %s", exc)
        return rows
    if not tables:
        return rows
    table = tables[0]
    for raw in table:
        names = {name.lower(): name for name in table.colnames}
        class_value = str(raw[names.get("class", names.get("best_class_name", table.colnames[0]))])
        astra_class = ""
        for token, mapped in class_map.items():
            if token.lower() in class_value.lower():
                astra_class = mapped
                break
        if not astra_class:
            continue
        ra_col = names.get("raj2000") or names.get("raicrs") or names.get("ra")
        dec_col = names.get("dej2000") or names.get("deicrs") or names.get("dec")
        if not ra_col or not dec_col:
            continue
        rows.append(_candidate_from_source({
            "tic_id": None,
            "name": str(raw[names.get("source", table.colnames[0])]),
            "ra": float(raw[ra_col]),
            "dec": float(raw[dec_col]),
            "astra_class": astra_class,
            "period": raw[names["period"]] if "period" in names else "",
            "catalog_label": class_value,
        }, "Gaia"))
    return rows


def _query_asas_sn_variability(target_per_class: int) -> list[dict[str, Any]]:
    """Query ASAS-SN variable candidates from VizieR when available."""
    from astroquery.vizier import Vizier

    rows: list[dict[str, Any]] = []
    type_map = {
        "RR": "rr_lyrae",
        "CEP": "cepheid",
        "EA": "eclipsing_binary",
        "EB": "eclipsing_binary",
        "EW": "eclipsing_binary",
    }
    try:
        viz = Vizier(columns=["**"], row_limit=target_per_class * 6)
        tables = viz.get_catalogs("II/366/catalog")
    except Exception as exc:
        log.warning("ASAS-SN adapter failed: %s", exc)
        return rows
    if not tables:
        return rows
    table = tables[0]
    names = {name.lower(): name for name in table.colnames}
    for raw in table:
        type_col = names.get("type") or names.get("vartype")
        if not type_col:
            continue
        type_value = str(raw[type_col])
        astra_class = ""
        for token, mapped in type_map.items():
            if type_value.upper().startswith(token):
                astra_class = mapped
                break
        if not astra_class:
            continue
        ra_col = names.get("raj2000") or names.get("ra")
        dec_col = names.get("dej2000") or names.get("dec")
        if not ra_col or not dec_col:
            continue
        rows.append(_candidate_from_source({
            "tic_id": None,
            "name": str(raw[names.get("name", type_col)]),
            "ra": float(raw[ra_col]),
            "dec": float(raw[dec_col]),
            "astra_class": astra_class,
            "period": raw[names["period"]] if "period" in names else "",
            "catalog_label": type_value,
        }, "ASAS-SN"))
    return rows


def _load_external_csv(path: Path, source_name: str) -> list[dict[str, Any]]:
    """Load Gaia, ASAS-SN, or future catalog exports from CSV.

    Accepted column names are intentionally simple:
    tic_id, name, ra, dec, astra_class, catalog_label, period.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    with open(path, newline="") as fp:
        reader = csv.DictReader(fp)
        for raw in reader:
            cls = raw.get("astra_class") or raw.get("class")
            if cls not in CLASS_NAMES:
                continue
            rows.append(_candidate_from_source({
                "tic_id": raw.get("tic_id"),
                "name": raw.get("name"),
                "ra": raw.get("ra"),
                "dec": raw.get("dec"),
                "astra_class": cls,
                "period": raw.get("period") or raw.get("catalog_period"),
                "catalog_label": raw.get("catalog_label") or raw.get("type"),
            }, source_name))
    return rows


def _candidate_from_source(row: dict[str, Any], source: str) -> dict[str, Any]:
    cls = row.get("astra_class", "")
    source_name = str(source or row.get("source") or "unknown")
    tic_id = normalize_tic_id(row.get("tic_id"))
    label = row.get("vsx_type") or row.get("catalog_label") or cls
    catalog_period = row.get("period", row.get("catalog_period"))
    if catalog_period in ("", None):
        catalog_period = ""

    return {
        "tic_id": tic_id,
        "source_catalogs": [source_name],
        "primary_source": source_name,
        "ra": row.get("ra", ""),
        "dec": row.get("dec", ""),
        "astra_class": cls,
        "catalog_label": label,
        "catalog_period": catalog_period,
        "crossmatch_status": "candidate",
        "label_confidence": "catalog_candidate",
        "tess_available": "",
        "cadence_candidates": "",
        "sector_candidates": "",
        "duplicate_group_id": "",
        "review_duplicate_group_id": "",
        "rejection_status": "",
        "name": row.get("name", ""),
        "vsx_type": row.get("vsx_type", ""),
        "label_conflict": "",
    }


def _merge_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge exact TIC duplicates while preserving source provenance."""
    merged: dict[str, dict[str, Any]] = {}
    coordinate_only: list[dict[str, Any]] = []

    for row in rows:
        tic = normalize_tic_id(row.get("tic_id"))
        if not tic:
            coordinate_only.append(row)
            continue
        if tic not in merged:
            row = dict(row)
            row["tic_id"] = tic
            merged[tic] = row
            continue
        existing = merged[tic]
        sources = set(existing.get("source_catalogs", [])) | set(row.get("source_catalogs", []))
        existing["source_catalogs"] = sorted(sources)
        if existing.get("astra_class") != row.get("astra_class"):
            existing["label_conflict"] = f"{existing.get('astra_class')}|{row.get('astra_class')}"
            existing["rejection_status"] = "label_conflict"
        if not existing.get("catalog_period") and row.get("catalog_period"):
            existing["catalog_period"] = row["catalog_period"]
        if not existing.get("ra") and row.get("ra"):
            existing["ra"] = row["ra"]
        if not existing.get("dec") and row.get("dec"):
            existing["dec"] = row["dec"]

    return list(merged.values()) + coordinate_only


def _verify_tess_availability(rows: list[dict[str, Any]], max_rows: int | None = None) -> list[dict[str, Any]]:
    try:
        import lightkurve as lk
    except ModuleNotFoundError as exc:
        verified = []
        for row in rows:
            row = dict(row)
            row["tess_available"] = "false"
            row["crossmatch_status"] = "tess_query_dependency_missing"
            row["rejection_status"] = f"tess_query_dependency_missing:{exc.name}"
            verified.append(row)
        return verified

    verified: list[dict[str, Any]] = []
    total_to_check = min(len(rows), max_rows) if max_rows is not None else len(rows)
    for idx, row in enumerate(rows):
        if max_rows is not None and idx >= max_rows:
            row = dict(row)
            row["tess_available"] = ""
            row["crossmatch_status"] = "not_checked"
            row["rejection_status"] = "pending_tess_check"
            verified.append(row)
            continue

        row = dict(row)
        target = f"TIC {row['tic_id']}" if row.get("tic_id") else row.get("name") or None
        if idx == 0 or (idx + 1) % 10 == 0:
            log.info("TESS availability check %d/%d", min(idx + 1, total_to_check), total_to_check)
        try:
            if row.get("tic_id"):
                search = lk.search_lightcurve(target, mission="TESS")
            elif row.get("ra") not in ("", None) and row.get("dec") not in ("", None):
                from astropy.coordinates import SkyCoord
                coord = SkyCoord(ra=float(row["ra"]), dec=float(row["dec"]), unit="deg")
                search = lk.search_lightcurve(coord, mission="TESS")
            else:
                search = lk.search_lightcurve(target, mission="TESS") if target else None
            if search is None or len(search) == 0:
                row["tess_available"] = "false"
                row["crossmatch_status"] = "no_tess_lightcurve"
                row["rejection_status"] = "no_tess_lightcurve"
            else:
                row["tess_available"] = "true"
                row["crossmatch_status"] = "tess_verified"
                row["rejection_status"] = ""
                try:
                    row["cadence_candidates"] = sorted(set(str(v) for v in search.table["exptime"]))
                except Exception:
                    row["cadence_candidates"] = ""
                try:
                    row["sector_candidates"] = sorted(set(str(v) for v in search.table["mission"]))
                except Exception:
                    row["sector_candidates"] = ""
        except Exception as exc:
            row["tess_available"] = "false"
            row["crossmatch_status"] = "tess_query_failed"
            row["rejection_status"] = f"tess_query_failed:{exc}"
        verified.append(row)
    return verified


def _apply_strict_label_policy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        row = dict(row)
        sources = set(row.get("source_catalogs", []))
        cls = row.get("astra_class")
        tess_ok = str(row.get("tess_available", "")).lower() == "true"

        if row.get("rejection_status"):
            out.append(row)
            continue
        if not tess_ok:
            row["rejection_status"] = "pending_tess_check"
        elif cls in VARIABLE_CLASSES and not sources:
            row["rejection_status"] = "missing_label_catalog"
        elif cls == "stable" and _looks_variable_source(sources):
            row["rejection_status"] = "stable_candidate_has_variable_source"
        else:
            row["label_confidence"] = "strict_confirmed"
            row["crossmatch_status"] = "strict_usable"
        out.append(row)
    return out


def _looks_variable_source(sources: set[str]) -> bool:
    joined = " ".join(sources).lower()
    return any(token in joined for token in ("vsx", "asas", "gaia_variable", "ogle"))


def _stable_has_local_variable_neighbor(row: dict[str, Any], all_rows: list[dict[str, Any]]) -> bool:
    try:
        ra = float(row.get("ra"))
        dec = float(row.get("dec"))
    except (TypeError, ValueError):
        return True
    for other in all_rows:
        if other is row or other.get("astra_class") == "stable":
            continue
        try:
            sep = angular_separation_arcsec(ra, dec, float(other.get("ra")), float(other.get("dec")))
        except (TypeError, ValueError):
            continue
        if sep <= 10.0:
            return True
    return False


def _stable_has_catalog_variable_match(row: dict[str, Any]) -> bool:
    """Check known variable catalogs around a stable candidate.

    If the remote check fails, fail closed by treating the candidate as not
    stable-confirmed.
    """
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier

        coord = SkyCoord(ra=float(row["ra"]), dec=float(row["dec"]), unit="deg")
        viz = Vizier(columns=["**"], row_limit=1)
        for catalog in ("B/vsx/vsx", "I/358/vclassre", "II/366/catalog"):
            try:
                tables = viz.query_region(coord, radius=10 * u.arcsec, catalog=catalog)
            except Exception:
                return True
            if tables and len(tables) > 0 and len(tables[0]) > 0:
                return True
    except Exception:
        return True
    return False


def _apply_stable_negative_screen(rows: list[dict[str, Any]], verify_remote: bool) -> list[dict[str, Any]]:
    screened: list[dict[str, Any]] = []
    for row in rows:
        row = dict(row)
        if row.get("astra_class") == "stable" and not row.get("rejection_status"):
            if _stable_has_local_variable_neighbor(row, rows):
                row["rejection_status"] = "stable_coordinate_variable_neighbor"
            elif verify_remote and _stable_has_catalog_variable_match(row):
                row["rejection_status"] = "stable_variable_catalog_match_or_check_failed"
            else:
                sources = set(row.get("source_catalogs", []))
                sources.add("stable_negative_screen")
                row["source_catalogs"] = sorted(sources)
        screened.append(row)
    return screened


def _limit_balanced(rows: list[dict[str, Any]], target_per_class: int) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    selected: list[dict[str, Any]] = []
    for row in rows:
        cls = row.get("astra_class")
        if cls not in CLASS_NAMES:
            continue
        if counts[cls] >= target_per_class:
            continue
        counts[cls] += 1
        selected.append(row)
    return selected


def _needs_more_candidates(rows: list[dict[str, Any]], target_per_class: int) -> bool:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        cls = row.get("astra_class")
        if cls in CLASS_NAMES:
            counts[cls] += 1
    return any(counts.get(cls, 0) < target_per_class for cls in CLASS_NAMES)


def _write_catalog_rejections(data_root: Path, rows: list[dict[str, Any]]) -> None:
    rejected_path = data_root / "rejected" / "rejected_samples.csv"
    existing = [
        row for row in read_csv_rows(rejected_path)
        if row.get("stage") != "catalog"
    ]
    write_csv_rows(rejected_path, existing, REJECTED_COLUMNS)
    for row in rows:
        status = row.get("rejection_status")
        if not status:
            continue
        append_csv_row(
            rejected_path,
            {
                "timestamp": utc_now(),
                "tic_id": row.get("tic_id", ""),
                "name": row.get("name", ""),
                "astra_class": row.get("astra_class", ""),
                "stage": "catalog",
                "reason": status,
                "source_catalogs": row.get("source_catalogs", ""),
                "primary_source": row.get("primary_source", ""),
            },
            REJECTED_COLUMNS,
        )


def build_phase6_catalog(
    data_root: Path = DEFAULT_PHASE6_ROOT,
    target_per_class: int = 200,
    use_network_catalogs: bool = False,
    verify_tess: bool = False,
    tess_check_limit: int | None = None,
    gaia_csv: Path | None = None,
    asas_sn_csv: Path | None = None,
) -> dict[str, Path]:
    data_root = ensure_phase6_structure(data_root)
    catalog_dir = data_root / "catalogs"

    rows = _load_legacy_catalog(limit_per_class=target_per_class)
    if use_network_catalogs or _needs_more_candidates(rows, target_per_class):
        rows.extend(_query_catalog_sources(target_per_class * 3))
        rows.extend(_query_gaia_variability(target_per_class))
        rows.extend(_query_asas_sn_variability(target_per_class))
    if gaia_csv:
        rows.extend(_load_external_csv(gaia_csv, "Gaia"))
    if asas_sn_csv:
        rows.extend(_load_external_csv(asas_sn_csv, "ASAS-SN"))

    rows = _merge_candidates(rows)
    rows = _limit_balanced(rows, target_per_class)
    rows = assign_duplicate_groups(rows)

    candidate_path = catalog_dir / "candidate_manifest.csv"
    write_csv_rows(candidate_path, rows, MANIFEST_COLUMNS)

    if verify_tess:
        resolved = _verify_tess_availability(rows, max_rows=tess_check_limit)
    else:
        resolved = []
        for row in rows:
            row = dict(row)
            row["crossmatch_status"] = "not_checked"
            row["rejection_status"] = "pending_tess_check"
            resolved.append(row)

    resolved = _apply_stable_negative_screen(resolved, verify_remote=verify_tess)
    resolved = _apply_strict_label_policy(resolved)
    resolved_path = catalog_dir / "resolved_manifest.csv"
    write_csv_rows(resolved_path, resolved, MANIFEST_COLUMNS)
    _write_catalog_rejections(data_root, resolved)

    usable = [row for row in resolved if not row.get("rejection_status")]
    usable_path = catalog_dir / "usable_manifest.csv"
    write_csv_rows(usable_path, usable, MANIFEST_COLUMNS)

    log.info("Wrote %d candidates to %s", len(rows), candidate_path)
    log.info("Wrote %d resolved rows to %s", len(resolved), resolved_path)
    log.info("Wrote %d usable rows to %s", len(usable), usable_path)

    return {
        "candidate_manifest": candidate_path,
        "resolved_manifest": resolved_path,
        "usable_manifest": usable_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ASTRA Phase 6 catalog manifests")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_PHASE6_ROOT)
    parser.add_argument("--target-per-class", type=int, default=200)
    parser.add_argument("--use-network-catalogs", action="store_true")
    parser.add_argument("--verify-tess", action="store_true")
    parser.add_argument("--tess-check-limit", type=int, default=None)
    parser.add_argument("--gaia-csv", type=Path, default=None)
    parser.add_argument("--asas-sn-csv", type=Path, default=None)
    args = parser.parse_args()

    build_phase6_catalog(
        data_root=args.data_root,
        target_per_class=args.target_per_class,
        use_network_catalogs=args.use_network_catalogs,
        verify_tess=args.verify_tess,
        tess_check_limit=args.tess_check_limit,
        gaia_csv=args.gaia_csv,
        asas_sn_csv=args.asas_sn_csv,
    )


if __name__ == "__main__":
    main()
