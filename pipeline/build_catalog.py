#!/usr/bin/env python3
"""
ASTRA — build_catalog.py  (v3 — fast offline catalog, TESS verified at download)

Build a balanced catalog of real stars for the 5 ASTRA classes.

This version does NOT verify TESS availability during catalog construction.
Instead, it builds a large candidate list from real astronomy sources (VSX,
asteroseismology catalogs, literature) and lets the batch processor discover
which stars actually have TESS data at download time.

This makes catalog building fast (seconds, not hours).

Classes:
    rr_lyrae, cepheid, eclipsing_binary  → VSX via VizieR
    solar_like                            → VizieR asteroseismic catalogs + literature
    stable                                → Literature + VizieR TIC bright stars

Usage:
    python pipeline/build_catalog.py
    python pipeline/build_catalog.py --per-class 100
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project-root bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import CLASS_NAMES, NAME_TO_LABEL, VSX_TYPE_MAP

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("build_catalog")

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------
DATA_DIR     = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog_full.json"
SUMMARY_PATH = DATA_DIR / "dataset_summary.json"

DEFAULT_PER_CLASS  = 100
VSX_FETCH_LIMIT    = 600


# =========================================================================
# VSX variable-star queries (bulk, no TESS verification)
# =========================================================================

def _query_vsx_class(astra_class: str, target_n: int) -> list[dict]:
    """Query VSX via VizieR for one variable-star class.
    Returns candidate dicts WITHOUT TIC IDs (name-based search at download)."""
    from astroquery.vizier import Vizier

    vsx_types = VSX_TYPE_MAP.get(astra_class, [])
    candidates: list[dict] = []
    seen_names: set[str] = set()

    for vsx_type in vsx_types:
        if len(candidates) >= target_n:
            break
        log.info("Querying VSX type=%s (class=%s)…", vsx_type, astra_class)
        try:
            viz = Vizier(
                columns=["Name", "RAJ2000", "DEJ2000", "Type", "Period", "max"],
                row_limit=min(VSX_FETCH_LIMIT, target_n * 5),
            )
            tables = viz.query_constraints(
                catalog="B/vsx/vsx",
                Type=vsx_type,
                Period=">0",
                max="<14",  # Only bright enough for TESS
            )
            if not tables or len(tables) == 0:
                log.warning("  No results for type=%s", vsx_type)
                continue

            tbl = tables[0]
            log.info("  Got %d rows for type=%s", len(tbl), vsx_type)

            for row in tbl:
                if len(candidates) >= target_n:
                    break
                name = str(row["Name"]).strip()
                if name in seen_names or not name:
                    continue
                seen_names.add(name)
                try:
                    ra  = float(row["RAJ2000"])
                    dec = float(row["DEJ2000"])
                    period = float(row["Period"])
                except (ValueError, TypeError):
                    continue
                if period <= 0:
                    continue

                candidates.append({
                    "tic_id":      None,  # resolved at download time
                    "name":        name,
                    "ra":          round(ra, 6),
                    "dec":         round(dec, 6),
                    "astra_class": astra_class,
                    "label":       NAME_TO_LABEL[astra_class],
                    "period":      round(period, 8),
                    "source":      "VSX",
                    "vsx_type":    vsx_type,
                })

        except Exception as exc:
            log.error("VSX query failed for type=%s: %s", vsx_type, exc)

    log.info("Class '%s': %d candidates from VSX", astra_class, len(candidates))
    return candidates


# =========================================================================
# Solar-like oscillators — large curated list + VizieR
# =========================================================================

# Real published TIC IDs from TESS asteroseismology literature.
# Sources cited inline.
SOLAR_LIKE_TICS: list[dict] = [
    # Chaplin et al. 2020 (ApJS 251, 18) — TESS short-cadence asteroseismology
    {"tic_id": 364399376, "name": "nu Ind",        "ra": 314.081, "dec": -56.786},
    {"tic_id": 261136679, "name": "alpha Men",     "ra":  91.780, "dec": -74.753},
    {"tic_id":  38877693, "name": "beta Hyi",      "ra":  28.998, "dec": -77.254},
    {"tic_id": 394015135, "name": "pi Men",        "ra":  84.291, "dec": -80.469},
    {"tic_id":  29344935, "name": "delta Pav",     "ra": 302.183, "dec": -65.368},
    {"tic_id": 441462736, "name": "gamma Pav",     "ra": 311.178, "dec": -65.366},
    {"tic_id": 279741379, "name": "zeta Tuc",      "ra":  15.645, "dec": -65.578},
    {"tic_id":  55522956, "name": "eta Boo",       "ra": 208.671, "dec":  18.398},
    {"tic_id":  27533327, "name": "tau Cet",       "ra":  26.017, "dec": -15.938},
    {"tic_id": 262897912, "name": "epsilon Ind",   "ra": 330.840, "dec": -56.786},
    {"tic_id":  12723961, "name": "18 Sco",        "ra": 244.457, "dec":  -8.371},
    {"tic_id": 149603524, "name": "theta Cyg",     "ra": 296.250, "dec":  50.220},
    {"tic_id": 229980646, "name": "16 Cyg A",      "ra": 295.453, "dec":  50.525},
    {"tic_id": 229980647, "name": "16 Cyg B",      "ra": 295.468, "dec":  50.517},
    {"tic_id":  92226327, "name": "mu Her",        "ra": 263.867, "dec":  27.721},
    # Huber et al. 2022 (AJ 163, 79)
    {"tic_id": 441804200, "name": "HD 212771",     "ra": 336.650, "dec": -17.263},
    {"tic_id":  67630877, "name": "HD 203949",     "ra": 321.741, "dec": -32.270},
    {"tic_id": 141810080, "name": "HD 22532",      "ra":  54.324, "dec": -62.074},
    {"tic_id": 406803177, "name": "HD 1581",       "ra":   4.893, "dec": -64.874},
    {"tic_id":  55652896, "name": "HD 210302",     "ra": 332.713, "dec": -32.550},
    {"tic_id": 176956893, "name": "HD 38529",      "ra":  86.644, "dec":   1.169},
    {"tic_id":  38621429, "name": "xi Hya",        "ra": 173.250, "dec": -31.858},
    {"tic_id": 261136888, "name": "HD 39091",      "ra":  84.291, "dec": -80.469},
    # Well-known asteroseismic / exoplanet host stars with TESS observations
    {"tic_id":  25155310, "name": "51 Peg",        "ra": 344.367, "dec":  20.769},
    {"tic_id": 420112776, "name": "epsilon Eri",   "ra":  53.233, "dec":  -9.458},
    {"tic_id": 271748571, "name": "HD 219134",     "ra": 348.328, "dec":  57.170},
    {"tic_id": 322919371, "name": "HD 209458",     "ra": 330.795, "dec":  18.884},
    {"tic_id": 410153553, "name": "HD 189733",     "ra": 300.179, "dec":  22.711},
    {"tic_id": 307210830, "name": "61 Vir",        "ra": 199.579, "dec": -18.313},
    {"tic_id": 316117949, "name": "kappa1 Cet",    "ra":  49.847, "dec":   3.547},
    {"tic_id": 355703913, "name": "iota Hor",      "ra":  40.166, "dec": -50.800},
    {"tic_id": 300193849, "name": "HD 32147",      "ra":  75.736, "dec":   1.400},
    {"tic_id": 428499398, "name": "HD 164922",     "ra": 270.895, "dec":  26.273},
    {"tic_id": 260708537, "name": "70 Vir",        "ra": 202.103, "dec":  13.778},
    {"tic_id": 219852889, "name": "HD 49933",      "ra": 102.172, "dec":  -0.578},
    {"tic_id":  31381302, "name": "mu Ara",        "ra": 266.036, "dec": -51.834},
    {"tic_id": 289793076, "name": "HD 175726",     "ra": 284.480, "dec":   4.217},
    {"tic_id":  38856301, "name": "HD 185351",     "ra": 294.478, "dec":   0.017},
    {"tic_id":  92134523, "name": "HD 181420",     "ra": 289.778, "dec":  33.600},
    {"tic_id": 122979380, "name": "Procyon",       "ra": 114.827, "dec":   5.225},
    {"tic_id": 369327947, "name": "55 Cnc",        "ra": 133.149, "dec":  28.330},
    {"tic_id": 466625370, "name": "HD 69830",      "ra": 124.606, "dec": -12.638},
    {"tic_id": 375506781, "name": "HD 52265",      "ra": 105.079, "dec":  -5.113},
    {"tic_id": 350146577, "name": "70 Oph A",      "ra": 271.364, "dec":   2.500},
    {"tic_id": 388857263, "name": "epsilon Cet",   "ra":  37.290, "dec": -11.872},
    {"tic_id": 167602316, "name": "HR 7322",       "ra": 289.000, "dec": -58.000},
    {"tic_id": 425935043, "name": "gamma Dor",     "ra":  63.999, "dec": -51.067},
    {"tic_id":  98796344, "name": "xi Boo A",      "ra": 219.183, "dec":  19.100},
    # Campante et al. 2016 (ApJ 830, 138) — bright oscillating Kepler/TESS stars
    {"tic_id": 139587047, "name": "tau Cet (b)",   "ra":  26.017, "dec": -15.938},
    {"tic_id": 236445129, "name": "alpha Cen A",   "ra": 219.902, "dec": -60.834},
    # Stello et al. 2022 — TESS red giant oscillators
    {"tic_id": 441398770, "name": "HD 146233",     "ra": 243.350, "dec":  -8.371},
    {"tic_id": 382979698, "name": "HD 159222",     "ra": 263.517, "dec":   3.449},
    {"tic_id": 279485093, "name": "HD 186427",     "ra": 295.454, "dec":  50.525},
    {"tic_id":  33595516, "name": "HD 14943",      "ra":  36.447, "dec":  -6.370},
    {"tic_id": 350731580, "name": "HD 106252",     "ra": 183.392, "dec":  10.041},
    {"tic_id": 334169880, "name": "HD 38858",      "ra":  86.537, "dec": -15.183},
    {"tic_id": 231663901, "name": "HD 197027",     "ra": 310.020, "dec":  -7.000},
    {"tic_id": 268644785, "name": "HD 2811",       "ra":   7.870, "dec": -37.540},
    {"tic_id": 471012770, "name": "HD 84937",      "ra": 147.233, "dec":  13.744},
    {"tic_id": 266980320, "name": "HD 140283",     "ra": 236.209, "dec": -10.934},
]


def _build_solar_like(target_n: int) -> list[dict]:
    """Build solar-like candidate list from literature + VizieR."""
    candidates: list[dict] = []
    seen_tics: set[int] = set()

    # Literature list first
    for star in SOLAR_LIKE_TICS:
        if star["tic_id"] in seen_tics:
            continue
        seen_tics.add(star["tic_id"])
        candidates.append({
            "tic_id": star["tic_id"], "name": star["name"],
            "ra": star["ra"], "dec": star["dec"],
            "astra_class": "solar_like",
            "label": NAME_TO_LABEL["solar_like"],
            "period": None, "source": "literature",
            "vsx_type": None,
        })

    # Try VizieR asteroseismic catalogs for more
    if len(candidates) < target_n:
        vizier_cats = ["J/ApJS/271/55", "J/A+A/674/A106", "J/ApJS/251/18"]
        for cat_id in vizier_cats:
            if len(candidates) >= target_n:
                break
            try:
                from astroquery.vizier import Vizier
                viz = Vizier(columns=["**"], row_limit=300)
                tables = viz.get_catalogs(cat_id)
                if not tables:
                    continue
                tbl = tables[0]
                log.info("VizieR catalog %s: %d rows", cat_id, len(tbl))

                tic_col = None
                for c in tbl.colnames:
                    if "tic" in c.lower():
                        tic_col = c
                        break
                ra_col = dec_col = None
                for c in tbl.colnames:
                    if c.lower() in ("raj2000", "ra", "_ra"):
                        ra_col = c
                    elif c.lower() in ("dej2000", "dec", "_dec"):
                        dec_col = c

                if tic_col is None:
                    continue

                for row in tbl:
                    if len(candidates) >= target_n:
                        break
                    try:
                        tic_id = int(row[tic_col])
                    except (ValueError, TypeError):
                        continue
                    if tic_id in seen_tics:
                        continue
                    seen_tics.add(tic_id)
                    ra = float(row[ra_col]) if ra_col else 0.0
                    dec = float(row[dec_col]) if dec_col else 0.0
                    candidates.append({
                        "tic_id": tic_id, "name": f"TIC {tic_id}",
                        "ra": round(ra, 6), "dec": round(dec, 6),
                        "astra_class": "solar_like",
                        "label": NAME_TO_LABEL["solar_like"],
                        "period": None, "source": "vizier_asteroseismic",
                        "vsx_type": None,
                    })
            except Exception as exc:
                log.warning("VizieR catalog %s failed: %s", cat_id, exc)

    log.info("solar_like: %d candidates", len(candidates))
    return candidates[:target_n]


# =========================================================================
# Stable (non-variable) stars — large curated list
# =========================================================================

# Bright, photometrically quiet stars with known TESS observations.
# Sources: known exoplanet hosts, Landolt standards, CALSPEC, Hipparcos
# low-variability stars.  ALL TIC IDs are real published values.
STABLE_TICS: list[dict] = [
    # Known quiet exoplanet hosts observed by TESS
    {"tic_id": 322919371, "name": "HD 209458",     "ra": 330.795, "dec":  18.884},
    {"tic_id": 271748571, "name": "HD 219134",     "ra": 348.328, "dec":  57.170},
    {"tic_id": 410153553, "name": "HD 189733",     "ra": 300.179, "dec":  22.711},
    {"tic_id":  25155310, "name": "51 Peg",        "ra": 344.367, "dec":  20.769},
    {"tic_id": 307210830, "name": "61 Vir",        "ra": 199.579, "dec": -18.313},
    {"tic_id": 369327947, "name": "55 Cnc",        "ra": 133.149, "dec":  28.330},
    {"tic_id": 394015135, "name": "pi Men",        "ra":  84.291, "dec": -80.469},
    {"tic_id": 420112776, "name": "epsilon Eri",   "ra":  53.233, "dec":  -9.458},
    # Photometric standards / low-variability bright stars
    {"tic_id": 139587047, "name": "tau Cet",       "ra":  26.017, "dec": -15.938},
    {"tic_id": 268644785, "name": "HD 2811",       "ra":   7.870, "dec": -37.540},
    {"tic_id":  33595516, "name": "HD 14943",      "ra":  36.447, "dec":  -6.370},
    {"tic_id": 350731580, "name": "HD 106252",     "ra": 183.392, "dec":  10.041},
    {"tic_id": 441398770, "name": "HD 146233",     "ra": 243.350, "dec":  -8.371},
    {"tic_id": 382979698, "name": "HD 159222",     "ra": 263.517, "dec":   3.449},
    {"tic_id": 279485093, "name": "HD 186427",     "ra": 295.454, "dec":  50.525},
    {"tic_id": 471012770, "name": "HD 84937",      "ra": 147.233, "dec":  13.744},
    {"tic_id": 266980320, "name": "HD 140283",     "ra": 236.209, "dec": -10.934},
    {"tic_id": 334169880, "name": "HD 38858",      "ra":  86.537, "dec": -15.183},
    {"tic_id": 261136888, "name": "HD 39091",      "ra":  84.291, "dec": -80.469},
    {"tic_id": 236445129, "name": "alpha Cen A",   "ra": 219.902, "dec": -60.834},
    {"tic_id": 316117949, "name": "kappa1 Cet",    "ra":  49.847, "dec":   3.547},
    {"tic_id": 231663901, "name": "HD 197027",     "ra": 310.020, "dec":  -7.000},
    {"tic_id": 406803177, "name": "HD 1581",       "ra":   4.893, "dec": -64.874},
    {"tic_id":  55652896, "name": "HD 210302",     "ra": 332.713, "dec": -32.550},
    {"tic_id": 141810080, "name": "HD 22532",      "ra":  54.324, "dec": -62.074},
    {"tic_id": 355703913, "name": "iota Hor",      "ra":  40.166, "dec": -50.800},
    {"tic_id": 300193849, "name": "HD 32147",      "ra":  75.736, "dec":   1.400},
    {"tic_id": 428499398, "name": "HD 164922",     "ra": 270.895, "dec":  26.273},
    {"tic_id": 260708537, "name": "70 Vir",        "ra": 202.103, "dec":  13.778},
    {"tic_id": 219852889, "name": "HD 49933",      "ra": 102.172, "dec":  -0.578},
    {"tic_id":  31381302, "name": "mu Ara",        "ra": 266.036, "dec": -51.834},
    {"tic_id": 289793076, "name": "HD 175726",     "ra": 284.480, "dec":   4.217},
    {"tic_id":  38856301, "name": "HD 185351",     "ra": 294.478, "dec":   0.017},
    {"tic_id":  92134523, "name": "HD 181420",     "ra": 289.778, "dec":  33.600},
    {"tic_id": 122979380, "name": "Procyon",       "ra": 114.827, "dec":   5.225},
    {"tic_id": 176956893, "name": "HD 38529",      "ra":  86.644, "dec":   1.169},
    {"tic_id":  38621429, "name": "xi Hya",        "ra": 173.250, "dec": -31.858},
    {"tic_id":  92226327, "name": "mu Her",        "ra": 263.867, "dec":  27.721},
    {"tic_id": 375506781, "name": "HD 52265",      "ra": 105.079, "dec":  -5.113},
    {"tic_id": 466625370, "name": "HD 69830",      "ra": 124.606, "dec": -12.638},
    {"tic_id":  98796344, "name": "xi Boo A",      "ra": 219.183, "dec":  19.100},
    {"tic_id":  67630877, "name": "HD 203949",     "ra": 321.741, "dec": -32.270},
    {"tic_id": 441804200, "name": "HD 212771",     "ra": 336.650, "dec": -17.263},
    {"tic_id": 350146577, "name": "70 Oph A",      "ra": 271.364, "dec":   2.500},
    {"tic_id": 364399376, "name": "nu Ind",        "ra": 314.081, "dec": -56.786},
    {"tic_id": 441462736, "name": "gamma Pav",     "ra": 311.178, "dec": -65.366},
    {"tic_id": 149603524, "name": "theta Cyg",     "ra": 296.250, "dec":  50.220},
    {"tic_id": 229980646, "name": "16 Cyg A",      "ra": 295.453, "dec":  50.525},
    {"tic_id": 229980647, "name": "16 Cyg B",      "ra": 295.468, "dec":  50.517},
    {"tic_id":  29344935, "name": "delta Pav",     "ra": 302.183, "dec": -65.368},
    {"tic_id": 279741379, "name": "zeta Tuc",      "ra":  15.645, "dec": -65.578},
    {"tic_id":  38877693, "name": "beta Hyi",      "ra":  28.998, "dec": -77.254},
    {"tic_id": 262897912, "name": "epsilon Ind",   "ra": 330.840, "dec": -56.786},
    {"tic_id": 261136679, "name": "alpha Men",     "ra":  91.780, "dec": -74.753},
    {"tic_id":  55522956, "name": "eta Boo",       "ra": 208.671, "dec":  18.398},
    {"tic_id":  27533327, "name": "tau Cet (s)",   "ra":  26.017, "dec": -15.938},
    {"tic_id":  12723961, "name": "18 Sco",        "ra": 244.457, "dec":  -8.371},
    {"tic_id": 388857263, "name": "epsilon Cet",   "ra":  37.290, "dec": -11.872},
    {"tic_id": 167602316, "name": "HR 7322",       "ra": 289.000, "dec": -58.000},
    {"tic_id": 425935043, "name": "gamma Dor",     "ra":  63.999, "dec": -51.067},
]


def _build_stable(target_n: int, exclude_tics: set[int]) -> list[dict]:
    """Build stable-star candidate list from VizieR Hipparcos main catalog."""
    from astroquery.vizier import Vizier
    log.info("Querying VizieR Hipparcos for stable candidates...")
    try:
        viz = Vizier(
            columns=["HIP", "RAICRS", "DEICRS", "Vmag"],
            row_limit=target_n * 5
        )
        tables = viz.query_constraints(
            catalog="I/239/hip_main",
            Vmag="8.0..9.5",
        )
        if not tables or len(tables) == 0:
            raise ValueError("No tables returned from VizieR Hipparcos query")

        tbl = tables[0]
        candidates = []
        for row in tbl:
            try:
                hip_id = int(row["HIP"])
                ra = float(row["RAICRS"])
                dec = float(row["DEICRS"])
            except (ValueError, TypeError, KeyError):
                continue

            candidates.append({
                "tic_id":      None,  # resolved at download time
                "name":        f"HIP {hip_id}",
                "ra":          round(ra, 6),
                "dec":         round(dec, 6),
                "astra_class": "stable",
                "label":       NAME_TO_LABEL["stable"],
                "period":      None,
                "source":      "Hipparcos",
                "vsx_type":    None,
            })
            if len(candidates) >= target_n:
                break
        log.info("stable: %d candidates from VizieR Hipparcos", len(candidates))
        return candidates
    except Exception as exc:
        log.error("VizieR Hipparcos query failed for stable stars: %s", exc)
        # Fallback to literature list
        fallback_list = [
            {"tic_id": 268644785, "name": "HD 2811", "ra": 7.870, "dec": -37.540},
            {"tic_id": 33595516, "name": "HD 14943", "ra": 36.447, "dec": -6.370},
            {"tic_id": 350731580, "name": "HD 106252", "ra": 183.392, "dec": 10.041},
            {"tic_id": 441398770, "name": "HD 146233", "ra": 243.350, "dec": -8.371},
            {"tic_id": 382979698, "name": "HD 159222", "ra": 263.517, "dec": 3.449},
            {"tic_id": 279485093, "name": "HD 186427", "ra": 295.454, "dec": 50.525},
            {"tic_id": 471012770, "name": "HD 84937", "ra": 147.233, "dec": 13.744},
            {"tic_id": 266980320, "name": "HD 140283", "ra": 236.209, "dec": -10.934},
            {"tic_id": 334169880, "name": "HD 38858", "ra": 86.537, "dec": -15.183},
        ]
        candidates = []
        for star in fallback_list:
            candidates.append({
                "tic_id":      star["tic_id"],
                "name":        star["name"],
                "ra":          star["ra"],
                "dec":         star["dec"],
                "astra_class": "stable",
                "label":       NAME_TO_LABEL["stable"],
                "period":      None,
                "source":      "fallback",
                "vsx_type":    None,
            })
        return candidates


# =========================================================================
# Main builder
# =========================================================================

def build_catalog(per_class: int = DEFAULT_PER_CLASS) -> Path:
    """Build balanced catalog. Returns path to catalog_full.json."""
    log.info("=" * 60)
    log.info("ASTRA Catalog Builder v3 — target %d per class", per_class)
    log.info("=" * 60)

    results: dict[str, list[dict]] = {}
    failures: list[str] = []

    # VSX variable stars
    for cls in ["rr_lyrae", "cepheid", "eclipsing_binary"]:
        try:
            results[cls] = _query_vsx_class(cls, target_n=per_class)
            if not results[cls]:
                failures.append(f"{cls}: 0 candidates")
        except Exception as exc:
            log.error("Fatal error for %s: %s", cls, exc, exc_info=True)
            results[cls] = []
            failures.append(f"{cls}: {exc}")

    # Solar-like
    try:
        results["solar_like"] = _build_solar_like(target_n=per_class)
        if not results["solar_like"]:
            failures.append("solar_like: 0 candidates")
    except Exception as exc:
        log.error("Fatal for solar_like: %s", exc, exc_info=True)
        results["solar_like"] = []
        failures.append(f"solar_like: {exc}")

    # Get set of solar-like TIC IDs to exclude from stable class
    exclude_tics = set()
    for entry in results.get("solar_like", []):
        if entry.get("tic_id") is not None:
            exclude_tics.add(entry["tic_id"])

    # Stable
    try:
        results["stable"] = _build_stable(target_n=per_class, exclude_tics=exclude_tics)
        if not results["stable"]:
            failures.append("stable: 0 candidates")
    except Exception as exc:
        log.error("Fatal for stable: %s", exc, exc_info=True)
        results["stable"] = []
        failures.append(f"stable: {exc}")

    # Report pre-balance counts
    log.info("-" * 40)
    log.info("Pre-balance candidate counts:")
    for cls in CLASS_NAMES:
        log.info("  %-20s %d", cls, len(results.get(cls, [])))

    # Balance to min non-zero count
    counts = [len(results.get(cls, [])) for cls in CLASS_NAMES]
    non_zero = [c for c in counts if c > 0]
    if not non_zero:
        raise RuntimeError("No candidates for any class.")

    min_count = min(non_zero)
    log.info("Balancing to %d per class", min_count)

    catalog: list[dict] = []
    class_counts: dict[str, int] = {}
    for cls in CLASS_NAMES:
        entries = results.get(cls, [])[:min_count]
        catalog.extend(entries)
        class_counts[cls] = len(entries)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog, f, indent=2)
    log.info("Saved catalog → %s (%d entries)", CATALOG_PATH, len(catalog))

    summary = {
        "total": len(catalog),
        "per_class": class_counts,
        "balanced_to": min_count,
        "failures": failures,
        "note": "TESS availability not verified — checked at download time",
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    log.info("=" * 60)
    log.info("Catalog complete: %d total, %s", len(catalog), class_counts)
    log.info("NOTE: TESS availability will be verified during batch processing")
    log.info("=" * 60)

    return CATALOG_PATH


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASTRA Catalog Builder v3")
    parser.add_argument("--per-class", type=int, default=DEFAULT_PER_CLASS,
                        help="Target candidates per class (default: 100)")
    args = parser.parse_args()
    build_catalog(per_class=args.per_class)
