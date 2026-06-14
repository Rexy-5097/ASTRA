#!/usr/bin/env python3
"""
ASTRA — preprocess.py

Process a single star from TIC ID to analysis-ready numpy arrays.

Pipeline steps:
    1. Download TESS light curves (SPOC preferred, any-author fallback)
    2. Quality filtering  (NaN, non-positive flux, quality bitmask)
    3. Sigma clipping     (5σ, 3 iterations via astropy)
    4. Sector stitching   (lightkurve stitch + normalisation)
    5. Detrending         (Savitzky-Golay trend removal)
    6. Period search      (Box Least Squares)
    7. Fixed-length array generation (flux_1000, flux_200)
   7b. Phase folding      (catalog or BLS period → folded_flux_1000/200)

Usage
-----
    python pipeline/preprocess.py <TIC_ID> <ASTRA_CLASS>
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import socket
import sys

# Set a default timeout of 120 seconds for all socket operations to prevent indefinite hangs
socket.setdefaulttimeout(120)

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Project-root bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.labels import NAME_TO_LABEL
from pipeline.phase6_utils import (
    PERIOD_REQUIRED_CLASSES,
    PHASE6_PREPROCESSING_VERSION,
    sha256_file,
    stable_json_hash,
    validate_phase6_metadata,
)


# ---------------------------------------------------------------------------
# Monkey Patch Lightkurve to handle custom HLSP FITS formats and signature bugs
# ---------------------------------------------------------------------------
def patch_lightkurve():
    try:
        import importlib

        import lightkurve as lk
        import lightkurve.io as lkio
        import lightkurve.search as lks

        lkread_mod = importlib.import_module('lightkurve.io.read')
        if hasattr(lkread_mod, "original_read"):
            return

        original_read = lkread_mod.read
        lkread_mod.original_read = original_read

        def custom_read_fits(path):
            import numpy as np
            from astropy.io import fits
            with fits.open(path) as hdus:
                data = None
                for hdu in hdus:
                    if isinstance(hdu, fits.BinTableHDU):
                        data = hdu.data
                        break
                if data is None:
                    raise ValueError("No BinTableHDU found in FITS file")

                cols = [c.lower() for c in data.columns.names]

                # Time column
                time_cols = ['time', 'time_bjd', 'tmid_bjd', 'tmid_utc', 'bjd', 'tmid']
                time_name = None
                for tc in time_cols:
                    if tc in cols:
                        time_name = data.columns.names[cols.index(tc)]
                        break
                if time_name is None:
                    for col in data.columns.names:
                        if 'time' in col.lower() or 'tmid' in col.lower():
                            time_name = col
                            break
                if time_name is None:
                    raise ValueError(f"Could not find time column in {data.columns.names}")

                # Flux column
                flux_cols = ['flux', 'sap_flux', 'pdcsap_flux', 'tfa1', 'tfa2', 'tfa3', 'ifl1', 'ifl2', 'ifl3', 'lc_flux']
                flux_name = None
                for fc in flux_cols:
                    if fc in cols:
                        flux_name = data.columns.names[cols.index(fc)]
                        break
                if flux_name is None:
                    for col in data.columns.names:
                        if 'flux' in col.lower() or 'ifl' in col.lower() or 'tfa' in col.lower():
                            flux_name = col
                            break
                if flux_name is None:
                    raise ValueError(f"Could not find flux column in {data.columns.names}")

                # Err column
                err_cols = ['flux_err', 'sap_flux_err', 'pdcsap_flux_err', 'ife1', 'ife2', 'ife3', 'lc_flux_err']
                err_name = None
                for ec in err_cols:
                    if ec in cols:
                        err_name = data.columns.names[cols.index(ec)]
                        break
                if err_name is None:
                    for col in data.columns.names:
                        if 'err' in col.lower() or 'ife' in col.lower():
                            err_name = col
                            break

                time_vals = data[time_name]
                flux_vals = data[flux_name]
                if err_name:
                    err_vals = data[err_name]
                else:
                    err_vals = np.zeros_like(flux_vals)

                if hasattr(time_vals, 'value'):
                    time_vals = time_vals.value
                if hasattr(flux_vals, 'value'):
                    flux_vals = flux_vals.value
                if hasattr(err_vals, 'value'):
                    err_vals = err_vals.value

                return lk.LightCurve(time=time_vals, flux=flux_vals, flux_err=err_vals)

        def patched_read(*args, **kwargs):
            try:
                return original_read(*args, **kwargs)
            except Exception as exc:
                path = args[0] if args else kwargs.get("path_or_url")
                if path and str(path).endswith(".fits"):
                    try:
                        return custom_read_fits(path)
                    except Exception:
                        raise exc
                raise exc

        lkread_mod.read = patched_read
        lkio.read = patched_read
        lk.read = patched_read
        lks.read = patched_read
    except Exception:
        pass

patch_lightkurve()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("preprocess")

# ---------------------------------------------------------------------------
# Default output directory
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FLUX_1000_LEN = 1000   # resampled full light-curve length
FLUX_200_LEN  = 200    # raw downsampled length
BLS_MIN_PERIOD = 0.1   # days (must be > BLS duration)
BLS_MAX_PERIOD = 50.0  # days
SAVGOL_WINDOW  = 301   # Savitzky-Golay window (must be odd)
SAVGOL_POLY    = 2     # Savitzky-Golay polynomial order


def _cleanup_star_dir(star_dir: Path | None, raw_star_dir: Path | None = None) -> None:
    """Remove partial output for a failed target."""
    if star_dir is not None and star_dir.exists():
        shutil.rmtree(star_dir)
    if raw_star_dir is not None and raw_star_dir.exists():
        shutil.rmtree(raw_star_dir)


def _select_period(
    catalog_period: float | None,
    bls_period: float | None,
) -> tuple[float | None, str]:
    """Select the single period source of truth."""
    if catalog_period is not None and np.isfinite(catalog_period) and catalog_period > 0:
        return float(catalog_period), "catalog"
    if bls_period is not None and np.isfinite(bls_period) and bls_period > 0:
        return float(bls_period), "BLS"
    return None, "unknown"


def _resample_normalized(values: np.ndarray, length: int) -> np.ndarray:
    """Interpolate a sequence to fixed length and normalize it."""
    x_original = np.linspace(0, 1, len(values))
    x_new = np.linspace(0, 1, length)
    arr = np.interp(x_new, x_original, values).astype(np.float32)
    std = arr.std()
    if std > 0:
        arr -= arr.mean()
        arr /= std
    return arr


def _phase_bin_normalized(
    time_arr: np.ndarray,
    flux_arr: np.ndarray,
    selected_period: float,
    length: int,
) -> np.ndarray:
    """Phase-fold and bin a flux sequence using selected_period."""
    phase = ((time_arr - time_arr[0]) % selected_period) / selected_period
    sort_idx = np.argsort(phase)
    phase_sorted = phase[sort_idx]
    flux_sorted = flux_arr[sort_idx]
    bin_edges = np.linspace(0, 1, length + 1)
    folded = np.zeros(length, dtype=np.float64)
    for i in range(length):
        mask = (phase_sorted >= bin_edges[i]) & (phase_sorted < bin_edges[i + 1])
        if np.any(mask):
            folded[i] = np.mean(flux_sorted[mask])
        else:
            folded[i] = np.interp((bin_edges[i] + bin_edges[i + 1]) / 2, phase_sorted, flux_sorted)
    nan_mask = ~np.isfinite(folded)
    if np.any(nan_mask):
        folded[nan_mask] = np.nanmean(folded[~nan_mask]) if np.any(~nan_mask) else 0.0
    folded = folded.astype(np.float32)
    std = folded.std()
    if std > 0:
        folded -= folded.mean()
        folded /= std
    return folded


# ===================================================================== #
#                      Core processing function                          #
# ===================================================================== #

def process_star(
    tic_id: int | None,
    astra_class: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_sectors: int = 10,
    search_name: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    force: bool = False,
    catalog_period: float | None = None,
    source_catalogs: list[str] | None = None,
    primary_source: str | None = None,
    catalog_label: str | None = None,
    duplicate_group_id: str | None = None,
    catalog_row: dict | None = None,
    preprocessing_version: str = PHASE6_PREPROCESSING_VERSION,
    raw_output_dir: Path | None = None,
) -> dict:
    """
    Download, clean, detrend, and resample a TESS light curve for a single
    star identified by its TIC ID or name.

    Parameters
    ----------
    tic_id : int or None
        TESS Input Catalog identifier.  If None, *search_name* is used.
    astra_class : str
        One of the 5 ASTRA class names (used for labelling only).
    output_dir : Path
        Root directory under which ``TIC_<tic_id>/`` is created.
    max_sectors : int
        Maximum number of TESS sectors to download.
    search_name : str or None
        Alternative search string (e.g. VSX name) when tic_id is unknown.
    catalog_period : float or None
        Known period from external catalog (e.g. VSX) in days.  Used for
        phase-folding when available; takes priority over BLS-derived period.

    Returns
    -------
    dict
        Metadata dictionary describing the processed star, or a dict with
        an ``"error"`` key if processing failed.

    Raises
    ------
    This function is designed *not* to raise — all exceptions are caught and
    returned as error dicts so the batch processor never crashes.
    """

    try:
        import lightkurve as lk
    except ModuleNotFoundError as exc:
        return {
            "tic_id": tic_id,
            "error": f"Missing required dependency for TESS download: {exc.name}",
            "stage": "download",
        }

    star_dir = None
    raw_star_dir = None
    output_dir = Path(output_dir)
    if raw_output_dir is None and output_dir.name == "processed" and output_dir.parent.name == "phase6":
        raw_output_dir = output_dir.parent / "raw"
    raw_output_dir = Path(raw_output_dir) if raw_output_dir is not None else None
    source_catalogs = source_catalogs or []
    if primary_source and primary_source not in source_catalogs:
        source_catalogs = [primary_source] + source_catalogs
    source_catalogs = sorted(set(str(s) for s in source_catalogs if str(s)))
    catalog_row = catalog_row or {}

    # Determine search target
    if tic_id is not None:
        target = f"TIC {tic_id}"
        # Cache check before doing any queries
        if not force:
            star_dir = output_dir / f"TIC_{tic_id}"
            meta_path = star_dir / "metadata.json"
            if (meta_path.exists()
                    and (star_dir / "flux_1000.npy").exists()
                    and (star_dir / "flux_200.npy").exists()
                    and (star_dir / "folded_flux_1000.npy").exists()
                    and (star_dir / "folded_flux_200.npy").exists()):
                try:
                    with open(meta_path) as fp:
                        metadata = json.load(fp)
                    if metadata.get("selected_period") is not None:
                        log.info("Star TIC %d already processed — loaded metadata from cache", tic_id)
                        return metadata
                except Exception:
                    pass
    elif search_name:
        target = search_name
    elif ra is not None and dec is not None:
        target = f"({ra},{dec})"
    else:
        return {"tic_id": None, "error": "No tic_id, search_name, or coordinates",
                "stage": "download"}

    log.info("Processing %s (class=%s)", target, astra_class)

    # ------------------------------------------------------------------ #
    # 1. Download
    # ------------------------------------------------------------------ #
    try:
        search = None
        # If TIC ID is available, search by target ID directly to avoid coordinate search overhead
        if tic_id is not None:
            log.info("Searching via target ID %s…", target)
            search = lk.search_lightcurve(target, mission="TESS", author="SPOC")
            if search is None or len(search) == 0:
                log.info("No SPOC data for target %s — trying any author…", target)
                search = lk.search_lightcurve(target, mission="TESS")

        # If coordinates are available and target search failed or was skipped, use coordinates
        if (search is None or len(search) == 0) and ra is not None and dec is not None:
            import astropy.units as u
            from astropy.coordinates import SkyCoord
            coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            log.info("Searching via coordinates (%.4f, %.4f) for %s…", ra, dec, target)
            search = lk.search_lightcurve(coord, mission="TESS", author="SPOC")
            if search is None or len(search) == 0:
                log.info("No SPOC data for coordinates of %s — trying any author…", target)
                search = lk.search_lightcurve(coord, mission="TESS")

        # Fallback to name search if coordinate search failed or coordinates not provided
        if search is None or len(search) == 0:
            log.info("Searching via name %s…", target)
            search = lk.search_lightcurve(target, mission="TESS", author="SPOC")
            if search is None or len(search) == 0:
                log.info("No SPOC data for name %s — trying any author…", target)
                search = lk.search_lightcurve(target, mission="TESS")

        if search is None or len(search) == 0:
            msg = f"No TESS light-curve data found for {target}"
            log.warning(msg)
            return {"tic_id": tic_id, "error": msg, "stage": "download"}

        # Extract TIC ID from search results if not provided
        if tic_id is None:
            try:
                tn = str(search.table["target_name"][0]).strip()
                if tn.isdigit():
                    tic_id = int(tn)
                elif "TIC" in tn.upper():
                    tic_id = int(tn.upper().replace("TIC", "").strip())
            except (KeyError, ValueError, IndexError):
                pass
            # Robust fallback: query MAST Catalogs by name or coordinates
            if tic_id is None:
                try:
                    from astroquery.mast import Catalogs
                    if target and not target.startswith("("):
                        catalog_data = Catalogs.query_object(target, catalog="TIC")
                        if len(catalog_data) > 0:
                            tic_id = int(catalog_data["ID"][0])
                            log.info("Resolved name %s to TIC %d via astroquery object search", target, tic_id)
                except Exception as e:
                    log.warning("astroquery Object search failed: %s", e)

            if tic_id is None and ra is not None and dec is not None:
                try:
                    import astropy.units as u
                    from astropy.coordinates import SkyCoord
                    from astroquery.mast import Catalogs
                    coord = SkyCoord(ra=ra, dec=dec, unit="deg")
                    catalog_data = Catalogs.query_region(coord, radius=0.01, catalog="TIC")
                    if len(catalog_data) > 0:
                        tic_id = int(catalog_data["ID"][0])
                        log.info("Resolved coordinates (%.4f, %.4f) to TIC %d via astroquery region search", ra, dec, tic_id)
                except Exception as e:
                    log.warning("astroquery Catalog search failed: %s", e)

            if tic_id is None:
                msg = f"Could not resolve TIC ID from search for {target}"
                log.warning(msg)
                return {"tic_id": None, "error": msg, "stage": "download"}
            log.info("Resolved %s → TIC %d", target, tic_id)

        # Cache check after resolving TIC ID
        if not force:
            star_dir = output_dir / f"TIC_{tic_id}"
            meta_path = star_dir / "metadata.json"
            if (meta_path.exists()
                    and (star_dir / "flux_1000.npy").exists()
                    and (star_dir / "flux_200.npy").exists()
                    and (star_dir / "folded_flux_1000.npy").exists()
                    and (star_dir / "folded_flux_200.npy").exists()):
                try:
                    with open(meta_path) as fp:
                        metadata = json.load(fp)
                    if metadata.get("selected_period") is not None:
                        log.info("Star TIC %d already processed — loaded metadata from cache", tic_id)
                        return metadata
                except Exception:
                    pass

        star_dir = output_dir / f"TIC_{tic_id}"
        star_dir.mkdir(parents=True, exist_ok=True)
        if raw_output_dir is not None:
            raw_star_dir = raw_output_dir / f"TIC_{tic_id}"

        # Limit to max_sectors
        if len(search) > max_sectors:
            log.info("Limiting from %d to %d sectors", len(search),
                     max_sectors)
            search = search[:max_sectors]

        lk_collection = search.download_all(quality_bitmask="default")
        if lk_collection is None or len(lk_collection) == 0:
            msg = f"Download returned empty collection for {target}"
            log.warning(msg)
            _cleanup_star_dir(star_dir, raw_star_dir)
            return {"tic_id": tic_id, "error": msg, "stage": "download"}

        # Clean unrecognized units that cause astropy vstack/stitch to fail
        import astropy.units as u
        for lc in lk_collection:
            for col in lc.colnames:
                col_unit = getattr(lc[col], 'unit', None)
                if col_unit is not None and isinstance(col_unit, u.UnrecognizedUnit):
                    ustr = str(col_unit).strip().lower()
                    val = lc[col].value if hasattr(lc[col], 'value') else np.asarray(lc[col])
                    if ustr in ['day', 'days']:
                        lc[col] = u.Quantity(val, unit=u.day)
                    else:
                        lc[col] = u.Quantity(val, unit=None)

        # Extract unique pipeline/author names for provenance tracking
        try:
            source_pipeline = ', '.join(
                sorted(set(str(a) for a in search.table['author'])))
        except Exception:
            source_pipeline = 'unknown'

        sector_information = []
        try:
            table = search.table
            for row in table:
                item = {}
                for key in ("mission", "author", "exptime", "target_name", "sequence_number"):
                    if key in table.colnames:
                        value = row[key]
                        item[key] = value.item() if hasattr(value, "item") else str(value)
                sector_information.append(item)
        except Exception:
            sector_information = []

        n_sectors = len(lk_collection)
        log.info("Downloaded %d sector(s) for %s (TIC %d)",
                 n_sectors, target, tic_id)


    except Exception as exc:
        msg = f"Download failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "download"}

    # ------------------------------------------------------------------ #
    # 2. Quality filtering
    # ------------------------------------------------------------------ #
    try:
        cleaned = []
        n_points_raw = 0
        source_cadence = None
        raw_file_hashes = {}

        for lc_index, lc in enumerate(lk_collection):
            n_points_raw += len(lc.flux)
            try:
                if raw_star_dir is not None:
                    raw_star_dir.mkdir(parents=True, exist_ok=True)
                    raw_path = raw_star_dir / f"lightcurve_{lc_index:03d}.npz"
                    np.savez_compressed(
                        raw_path,
                        time=np.asarray(lc.time.value, dtype=np.float64),
                        flux=np.asarray(lc.flux.value, dtype=np.float64),
                        flux_err=np.asarray(getattr(lc.flux_err, "value", lc.flux_err), dtype=np.float64)
                        if getattr(lc, "flux_err", None) is not None else np.array([], dtype=np.float64),
                        meta=json.dumps({
                            "targetid": lc.meta.get("TARGETID"),
                            "sector": lc.meta.get("SECTOR"),
                            "author": lc.meta.get("AUTHOR"),
                        }, sort_keys=True),
                    )
                    raw_file_hashes[str(raw_path.relative_to(raw_output_dir.parent))] = sha256_file(raw_path)
                else:
                    raw_file_hashes[f"lightcurve_{lc_index}"] = stable_json_hash({
                        "time_points": len(lc.time.value),
                        "flux_points": len(lc.flux.value),
                        "targetid": lc.meta.get("TARGETID"),
                        "sector": lc.meta.get("SECTOR"),
                        "author": lc.meta.get("AUTHOR"),
                    })
            except Exception:
                raw_file_hashes[f"lightcurve_{lc_index}"] = "unavailable"

            # Record cadence from the first light curve
            if source_cadence is None:
                try:
                    dt = np.nanmedian(np.diff(lc.time.value))
                    source_cadence = round(dt * 24 * 60, 1)  # minutes
                except Exception:
                    source_cadence = None

            # Remove NaN flux
            mask = np.isfinite(np.asarray(lc.flux.value))
            lc = lc[mask]

            # Remove non-positive flux
            mask = np.asarray(lc.flux.value) > 0
            lc = lc[mask]

            if len(lc) > 10:
                cleaned.append(lc)

        if not cleaned:
            msg = f"No usable data after quality filtering for {target}"
            log.warning(msg)
            _cleanup_star_dir(star_dir, raw_star_dir)
            return {"tic_id": tic_id, "error": msg, "stage": "quality"}

    except Exception as exc:
        msg = f"Quality filtering failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "quality"}

    # ------------------------------------------------------------------ #
    # 3. Sigma clipping
    # ------------------------------------------------------------------ #
    try:
        from astropy.stats import sigma_clip

        sigma_cleaned = []
        for lc in cleaned:
            flux_vals = np.asarray(lc.flux.value).copy()
            # Use masked=True to get a MaskedArray, where True indicates values that were clipped
            clipped = sigma_clip(flux_vals, sigma=5, maxiters=3, masked=True)
            mask = ~np.ma.getmaskarray(clipped)
            lc = lc[mask]
            if len(lc) > 10:
                sigma_cleaned.append(lc)

        if not sigma_cleaned:
            msg = f"No data left after sigma clipping for {target}"
            log.warning(msg)
            _cleanup_star_dir(star_dir, raw_star_dir)
            return {"tic_id": tic_id, "error": msg, "stage": "sigma_clip"}

        cleaned = sigma_cleaned

    except Exception as exc:
        msg = f"Sigma clipping failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "sigma_clip"}

    # ------------------------------------------------------------------ #
    # 4. Sector stitching
    # ------------------------------------------------------------------ #
    try:
        if len(cleaned) > 1:
            # Reconstruct a LightCurveCollection for stitching
            collection = lk.LightCurveCollection(cleaned)
            stitched = collection.stitch(
                corrector_func=lambda x: x.normalize()
            )
        else:
            stitched = cleaned[0].normalize()

        time_arr = stitched.time.value.astype(np.float64)
        flux_arr = stitched.flux.value.astype(np.float64)

        # Final NaN check after stitching
        valid = np.isfinite(time_arr) & np.isfinite(flux_arr)
        time_arr = time_arr[valid]
        flux_arr = flux_arr[valid]

        n_points_clean = len(flux_arr)
        if n_points_clean < 50:
            msg = (f"Only {n_points_clean} points after stitching "
                   f"for {target}")
            log.warning(msg)
            _cleanup_star_dir(star_dir, raw_star_dir)
            return {"tic_id": tic_id, "error": msg, "stage": "stitch"}

        log.info("Stitched: %d clean points", n_points_clean)

    except Exception as exc:
        msg = f"Stitching failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "stitch"}

    # ------------------------------------------------------------------ #
    # 5. Detrending  (Savitzky-Golay)
    # ------------------------------------------------------------------ #
    try:
        from scipy.signal import savgol_filter

        window = SAVGOL_WINDOW
        # Window must be odd and less than data length
        if window >= len(flux_arr):
            window = len(flux_arr) // 2 * 2 - 1  # largest odd < length
            if window < 5:
                window = 5
        if window % 2 == 0:
            window -= 1

        trend = savgol_filter(flux_arr, window_length=window,
                              polyorder=SAVGOL_POLY)
        detrended = flux_arr - trend

    except Exception as exc:
        msg = f"Detrending failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "detrend"}

    # ------------------------------------------------------------------ #
    # 6. Period search  (Box Least Squares)
    # ------------------------------------------------------------------ #
    bls_period = None
    bls_power = None
    try:
        from astropy.timeseries import BoxLeastSquares

        if len(time_arr) >= 100:
            bls = BoxLeastSquares(time_arr, detrended)
            period_grid = np.linspace(BLS_MIN_PERIOD, BLS_MAX_PERIOD, 5000)
            result = bls.power(period_grid, duration=0.05)

            best_idx = np.argmax(result.power)
            bls_period = float(result.period[best_idx])
            bls_power = float(result.power[best_idx])
            log.info("BLS best period: %.6f d  (power=%.4f)",
                     bls_period, bls_power)
        else:
            log.info("Too few points (%d) for BLS — skipping period search",
                     len(time_arr))

    except Exception as exc:
        log.warning("BLS period search failed for %s: %s", target, exc)
        bls_period = None
        bls_power = None

    # ------------------------------------------------------------------ #
    # 6b. Period Precedence Logic
    #
    # Establish a SINGLE SOURCE OF TRUTH for periods:
    # 1. catalog_period: If available and > 0, we prefer it because it comes
    #    from long-baseline, expert-vetted databases (like VSX, ASAS-SN) and is
    #    highly reliable.
    # 2. bls_period: If catalog_period is not available, we fall back to the
    #    BLS period estimated from the current TESS sectors.
    # 3. None: If neither is available, phase folding cannot be performed.
    # ------------------------------------------------------------------ #
    selected_period, period_source = _select_period(catalog_period, bls_period)

    if selected_period is None:
        required_note = "required for folded periodic classes" if astra_class in PERIOD_REQUIRED_CLASSES else "required by Phase 6 metadata contract"
        msg = f"No valid selected_period for {target}; {required_note}"
        log.warning(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "period"}

    # ------------------------------------------------------------------ #
    # 7. Fixed-length arrays
    # ------------------------------------------------------------------ #
    try:
        # Raw arrays are time-order preserving. Folding only happens in
        # folded_flux_*.npy below.
        flux_1000 = _resample_normalized(detrended, FLUX_1000_LEN)
        flux_200 = _resample_normalized(detrended, FLUX_200_LEN)

        # --- Save arrays ---
        np.save(star_dir / "flux_1000.npy", flux_1000)
        np.save(star_dir / "flux_200.npy", flux_200)
        log.info("Saved flux arrays → %s", star_dir)

    except Exception as exc:
        msg = f"Array generation failed for {target}: {exc}"
        log.error(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "array_gen"}

    # ------------------------------------------------------------------ #
    # 7b. Phase folding (using selected_period)
    #
    # Science note: Phase-folding converts a time-series light curve into
    # a single-cycle profile by wrapping time modulo the orbital/pulsation
    # period.  This dramatically boosts the SNR for periodic signals and
    # is the standard representation for classifying eclipsing binaries,
    # Cepheids, and RR Lyrae stars.
    # ------------------------------------------------------------------ #
    has_folded_lc = False

    try:
        if selected_period is not None:
            folded_flux_1000 = _phase_bin_normalized(time_arr, detrended, selected_period, FLUX_1000_LEN)
            folded_flux_200 = _phase_bin_normalized(time_arr, detrended, selected_period, FLUX_200_LEN)

            np.save(star_dir / "folded_flux_1000.npy", folded_flux_1000)
            np.save(star_dir / "folded_flux_200.npy", folded_flux_200)
            has_folded_lc = True
            log.info("Phase-folded (period=%.6f d, source=%s) → %s",
                     selected_period, period_source, star_dir)
        else:
            msg = f"No valid period for {target}; folded arrays were not created"
            log.warning(msg)
            _cleanup_star_dir(star_dir, raw_star_dir)
            return {"tic_id": tic_id, "error": msg, "stage": "phase_fold"}

    except Exception as exc:
        msg = f"Phase folding failed for {target}: {exc}"
        log.warning(msg)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "phase_fold"}

    # ------------------------------------------------------------------ #
    # 8. Metadata
    # ------------------------------------------------------------------ #
    # --- Derived quality / characterisation metrics ---
    # cadence_type: short-cadence (≤2.1 min) vs long-cadence
    cadence_type = 'short' if (source_cadence is not None and source_cadence <= 2.1) else 'long'

    # variability_amplitude: 90th-percentile range of detrended flux
    variability_amplitude = float(
        np.percentile(detrended, 95) - np.percentile(detrended, 5))

    # estimated_snr: signal power relative to high-frequency noise
    #   Uses the differenced series as a proxy for white noise (high-pass
    #   filter), then corrects by √2 because diff doubles noise variance.
    diff_std = np.std(np.diff(detrended))
    estimated_snr = float(
        np.std(detrended) / diff_std * np.sqrt(2)) if diff_std > 0 else 0.0

    processed_file_hashes = {}
    for filename in (
        "flux_1000.npy",
        "flux_200.npy",
        "folded_flux_1000.npy",
        "folded_flux_200.npy",
    ):
        path = star_dir / filename
        if path.exists():
            processed_file_hashes[filename] = sha256_file(path)

    hash_payload = {
        "preprocessing_version": preprocessing_version,
        "tic_id": tic_id,
        "astra_class": astra_class,
        "ra": ra,
        "dec": dec,
        "source_catalogs": source_catalogs,
        "primary_source": primary_source,
        "catalog_label": catalog_label,
        "catalog_period": catalog_period,
        "bls_period": bls_period,
        "selected_period": selected_period,
        "period_source": period_source,
        "raw_file_hashes": raw_file_hashes,
        "processed_file_hashes": processed_file_hashes,
        "max_sectors": max_sectors,
        "savgol_window": SAVGOL_WINDOW,
        "savgol_poly": SAVGOL_POLY,
        "bls_min_period": BLS_MIN_PERIOD,
        "bls_max_period": BLS_MAX_PERIOD,
        "catalog_row": catalog_row,
    }
    preprocessing_hash = stable_json_hash(hash_payload)

    metadata = {
        "tic_id":              tic_id,
        "astra_class":         astra_class,
        "label":               NAME_TO_LABEL.get(astra_class, -1),
        "source_catalogs":     source_catalogs,
        "primary_source":      primary_source or (source_catalogs[0] if source_catalogs else "unknown"),
        "catalog_label":       catalog_label,
        "ra":                  ra,
        "dec":                 dec,
        "n_sectors":           n_sectors,
        "n_points_raw":        n_points_raw,
        "n_points_clean":      n_points_clean,
        "selected_period":     selected_period,
        "period":              selected_period,
        "bls_period":          bls_period,
        "catalog_period":      catalog_period,
        "bls_power":           bls_power,
        "source_cadence":      source_cadence,
        "cadence_type":        cadence_type,
        "sector_information":  sector_information,
        "source_pipeline":     source_pipeline,
        "variability_amplitude": variability_amplitude,
        "snr_estimate":        estimated_snr,
        "estimated_snr":       estimated_snr,
        "period_source":       period_source,
        "has_folded_lc":       has_folded_lc,
        "duplicate_group_id":  duplicate_group_id,
        "preprocessing_version": preprocessing_version,
        "preprocessing_hash":  preprocessing_hash,
        "raw_file_hashes":     raw_file_hashes,
        "processed_file_hashes": processed_file_hashes,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    metadata_errors = validate_phase6_metadata(metadata)
    if metadata_errors:
        msg = "Metadata validation failed: " + "; ".join(metadata_errors)
        log.error("%s for %s", msg, target)
        _cleanup_star_dir(star_dir, raw_star_dir)
        return {"tic_id": tic_id, "error": msg, "stage": "metadata"}

    meta_path = star_dir / "metadata.json"
    with open(meta_path, "w") as fp:
        json.dump(metadata, fp, indent=2)
    log.info("Saved metadata → %s", meta_path)

    return metadata


# ===================================================================== #
#                      Entry point                                       #
# ===================================================================== #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ASTRA — Preprocess a single TESS star",
    )
    parser.add_argument("tic_id", type=int,
                        help="TESS Input Catalog ID")
    parser.add_argument("astra_class", type=str,
                        help="ASTRA class name "
                             "(rr_lyrae|cepheid|eclipsing_binary"
                             "|solar_like|stable)")
    parser.add_argument("--output-dir", type=Path,
                        default=DEFAULT_OUTPUT_DIR,
                        help="Root output directory "
                             "(default: data/processed)")
    parser.add_argument("--max-sectors", type=int, default=10,
                        help="Max TESS sectors to download (default: 10)")
    args = parser.parse_args()

    if args.astra_class not in NAME_TO_LABEL:
        parser.error(f"Unknown class '{args.astra_class}'.  "
                     f"Choose from: {list(NAME_TO_LABEL.keys())}")

    result = process_star(
        tic_id=args.tic_id,
        astra_class=args.astra_class,
        output_dir=args.output_dir,
        max_sectors=args.max_sectors,
    )

    if "error" in result:
        log.error("FAILED: %s", result["error"])
        sys.exit(1)
    else:
        log.info("SUCCESS: TIC %d processed", args.tic_id)
