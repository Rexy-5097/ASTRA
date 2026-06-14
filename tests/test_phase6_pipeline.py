from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from data.labels import CLASS_NAMES, NAME_TO_LABEL
from pipeline.dataset_audit import run_audit
from pipeline.download_manager import _row_is_processable, download_phase6
from pipeline.freeze_phase6_splits import freeze_splits
from pipeline.phase6_utils import (
    REJECTED_COLUMNS,
    append_csv_row,
    array_content_hash,
    assert_phase6_training_allowed,
    assign_duplicate_groups,
    sha256_file,
    stable_json_hash,
)
from pipeline.preprocess import (
    _cleanup_star_dir,
    _phase_bin_normalized,
    _resample_normalized,
    _select_period,
)


def _normalized_array(length: int) -> np.ndarray:
    arr = np.linspace(-1.0, 1.0, length, dtype=np.float32)
    arr -= arr.mean()
    arr /= arr.std()
    return arr


def _write_sample(root: Path, tic_id: int, cls: str, group: str, ra: float, dec: float) -> None:
    star_dir = root / "processed" / f"TIC_{tic_id}"
    star_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "raw" / f"TIC_{tic_id}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "lightcurve_000.npz"
    np.savez_compressed(raw_path, time=np.arange(10), flux=np.ones(10))
    arrays = {
        "flux_1000.npy": _normalized_array(1000),
        "flux_200.npy": _normalized_array(200),
        "folded_flux_1000.npy": _normalized_array(1000),
        "folded_flux_200.npy": _normalized_array(200),
    }
    for filename, arr in arrays.items():
        np.save(star_dir / filename, arr)
    processed_hashes = {
        filename: sha256_file(star_dir / filename)
        for filename in arrays
    }
    metadata = {
        "tic_id": tic_id,
        "astra_class": cls,
        "label": NAME_TO_LABEL[cls],
        "source_catalogs": ["unit_test"],
        "primary_source": "unit_test",
        "catalog_label": cls,
        "ra": ra,
        "dec": dec,
        "n_sectors": 1,
        "n_points_raw": 1000,
        "n_points_clean": 1000,
        "selected_period": 1.234,
        "period": 1.234,
        "bls_period": 1.234,
        "catalog_period": None,
        "bls_power": 1.0,
        "source_cadence": 30.0,
        "cadence_type": "long",
        "sector_information": [{"mission": "TESS Sector 1"}],
        "source_pipeline": "unit_test",
        "variability_amplitude": 0.2,
        "snr_estimate": 5.0,
        "estimated_snr": 5.0,
        "period_source": "BLS",
        "has_folded_lc": True,
        "duplicate_group_id": group,
        "preprocessing_version": "unit_test",
        "raw_file_hashes": {str(raw_path.relative_to(root)): sha256_file(raw_path)},
        "processed_file_hashes": processed_hashes,
        "preprocessing_hash": stable_json_hash({"tic_id": tic_id}),
        "processing_timestamp": "2026-05-27T00:00:00+00:00",
    }
    (star_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))


class Phase6PipelineTests(unittest.TestCase):
    def test_period_precedence_catalog_then_bls_then_reject(self) -> None:
        self.assertEqual(_select_period(2.5, 1.0), (2.5, "catalog"))
        self.assertEqual(_select_period(None, 1.0), (1.0, "BLS"))
        self.assertEqual(_select_period(float("nan"), None), (None, "unknown"))

    def test_flux_200_is_raw_downsample_not_folded(self) -> None:
        time = np.linspace(0, 10, 1000)
        flux = np.sin(time) + 0.1 * time
        raw_200 = _resample_normalized(flux, 200)
        folded_200 = _phase_bin_normalized(time, flux, 2.0, 200)
        self.assertEqual(raw_200.shape, (200,))
        self.assertEqual(folded_200.shape, (200,))
        self.assertGreater(float(np.max(np.abs(raw_200 - folded_200))), 0.1)

    def test_failed_cleanup_removes_processed_and_raw_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed" / "TIC_1"
            raw = root / "raw" / "TIC_1"
            processed.mkdir(parents=True)
            raw.mkdir(parents=True)
            (processed / "partial.npy").write_text("bad")
            (raw / "partial.npz").write_text("bad")
            _cleanup_star_dir(processed, raw)
            self.assertFalse(processed.exists())
            self.assertFalse(raw.exists())

    def test_download_manager_is_strict_by_default(self) -> None:
        self.assertFalse(_row_is_processable({"rejection_status": "pending_tess_check"}, False))
        self.assertTrue(_row_is_processable({"rejection_status": ""}, False))

    def test_download_gate_refuses_insufficient_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "phase6"
            (root / "catalogs").mkdir(parents=True)
            (root / "catalogs" / "usable_manifest.csv").write_text(
                "tic_id,rejection_status,astra_class\n1,,rr_lyrae\n"
            )
            summary = download_phase6(root, max_usable=2)
            self.assertIn("error", summary)

    def test_duplicate_groups_use_tic_and_coordinates(self) -> None:
        rows = assign_duplicate_groups([
            {"tic_id": "100", "ra": 10.0, "dec": 10.0},
            {"tic_id": "100", "ra": 20.0, "dec": 20.0},
            {"tic_id": "", "ra": 30.0, "dec": 30.0},
            {"tic_id": "", "ra": 30.0001, "dec": 30.0001},
        ])
        self.assertEqual(rows[0]["duplicate_group_id"], rows[1]["duplicate_group_id"])
        self.assertEqual(rows[2]["duplicate_group_id"], rows[3]["duplicate_group_id"])

    def test_audit_and_freeze_on_synthetic_phase6_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "phase6"
            tic = 1000
            for class_index, cls in enumerate(CLASS_NAMES):
                for offset in range(3):
                    _write_sample(
                        root,
                        tic,
                        cls,
                        f"group_{tic}",
                        10.0 + class_index,
                        -20.0 - offset,
                    )
                    tic += 1

            append_csv_row(
                root / "rejected" / "rejected_samples.csv",
                {
                    "timestamp": "2026-05-27T00:00:00+00:00",
                    "tic_id": "999",
                    "name": "bad",
                    "astra_class": "rr_lyrae",
                    "stage": "download",
                    "reason": "unit test rejection",
                    "source_catalogs": "unit_test",
                    "primary_source": "unit_test",
                },
                REJECTED_COLUMNS,
            )

            freeze_splits(root, minimum_samples=1, allow_unpassed_audit=True)
            status = run_audit(root, stage=0)

            self.assertEqual(status["overall_status"], "PASS")
            for report in status["reports"]:
                self.assertTrue((root / "audits" / report).exists())

    def test_training_guard_refuses_unverified_phase6_path(self) -> None:
        from unittest.mock import patch

        from pipeline import phase6_utils

        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "fake_phase6"
            with patch.object(phase6_utils, "DEFAULT_PHASE6_ROOT", fake_root):
                with self.assertRaises(RuntimeError):
                    assert_phase6_training_allowed(fake_root / "processed")

    def test_array_hash_is_stable(self) -> None:
        arr = _normalized_array(1000)
        self.assertEqual(array_content_hash(arr), array_content_hash(arr.copy()))

    def test_raw_file_hash_changes_when_input_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.npz"
            np.savez_compressed(path, time=np.arange(3), flux=np.ones(3))
            first = sha256_file(path)
            np.savez_compressed(path, time=np.arange(3), flux=np.arange(3))
            second = sha256_file(path)
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
