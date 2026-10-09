import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import generate_rainfall_scenarios as rainfall


class RainfallScenarioTests(unittest.TestCase):
    def test_profile_and_targets(self):
        profile = rainfall.normalized_profile()
        self.assertEqual(len(profile), 12)
        self.assertAlmostEqual(sum(profile), 1.0)
        records = rainfall.generate_all_records()
        validation = rainfall.validate_records(records)
        self.assertEqual(validation["record_count"], 204)
        self.assertAlmostEqual(validation["historical_total_mm"], 944.2, places=2)
        for result in validation["peak_scenarios"].values():
            self.assertAlmostEqual(result["peak_intensity_mm_per_hr"], result["target_peak_intensity_mm_per_hr"], places=5)
        for result in validation["depth_scenarios"].values():
            self.assertAlmostEqual(result["total_depth_mm"], result["target_total_depth_mm"], places=5)

    def test_catalogue_integrity_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = rainfall.write_outputs(Path(temp_dir))
            self.assertTrue(result["written"])
            with (Path(temp_dir) / "swmm_rainfall_catalog.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 204)
            self.assertEqual(set(row["timeseries_id"] for row in rows), set(rainfall.EXPECTED_IDS))
            for row in rows:
                tolerance = 0.01 if row["timeseries_id"] == "TS_2005_JULY26" else 0.00001
                self.assertLessEqual(
                    abs(float(row["intensity_mm_per_hr"]) - float(row["rainfall_15min_mm"]) * 4.0),
                    tolerance,
                )
                self.assertTrue(row["datetime"])
            metadata = json.loads((Path(temp_dir) / "swmm_rainfall_metadata.json").read_text(encoding="utf-8"))
            self.assertIn("source_data_limitations", metadata)
            self.assertIn("TS_2005_JULY26", metadata["scenarios"])

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "outputs"
            result = rainfall.write_outputs(output_dir, dry_run=True)
            self.assertFalse(result["written"])
            self.assertFalse(output_dir.exists())

    def test_generation_is_deterministic_except_metadata_timestamp(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            rainfall.write_outputs(Path(left))
            rainfall.write_outputs(Path(right))
            for name in rainfall.OUTPUT_NAMES:
                if name.endswith(".json"):
                    continue
                self.assertEqual(
                    hashlib.sha256((Path(left) / name).read_bytes()).digest(),
                    hashlib.sha256((Path(right) / name).read_bytes()).digest(),
                )

    def test_validation_failure_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            sentinel = output_dir / "timeseries_2005_july26.dat"
            sentinel.write_text("existing\n", encoding="utf-8")
            with patch.object(rainfall, "generate_all_records", return_value=[]):
                with self.assertRaises(ValueError):
                    rainfall.write_outputs(output_dir)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing\n")

    def test_hydraulic_outputs_are_not_created_or_changed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            rainfall.write_outputs(output_dir)
            self.assertFalse((output_dir / "swmm_junctions_citywide.csv").exists())
            self.assertFalse((output_dir / "swmm_conduits_citywide.csv").exists())
            self.assertFalse((output_dir / "pilot_ward_L").exists())


if __name__ == "__main__":
    unittest.main()
