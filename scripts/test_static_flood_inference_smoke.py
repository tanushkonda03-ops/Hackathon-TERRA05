"""Artifact round-trip and real-row prediction smoke test; no quality metrics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from static_flood_inference import DEFAULT_ARTIFACT_PATH, FEATURES, StaticFloodPredictor


class StaticFloodInferenceSmokeTest(unittest.TestCase):
    def test_saved_pipeline_loads_and_predicts_real_dataset_row(self):
        self.assertTrue(DEFAULT_ARTIFACT_PATH.is_file(), "Run the training script to create the artifact")
        dataset = ROOT / "data" / "ml_ready" / "ml_master_spatial_features.csv"
        row = pd.read_csv(dataset, usecols=list(FEATURES), nrows=1).iloc[0]
        prediction = StaticFloodPredictor().predict(row.to_dict())

        self.assertIn("model_score", prediction)
        self.assertIn("predicted_class_at_selected_development_threshold", prediction)
        self.assertGreaterEqual(prediction["model_score"], 0.0)
        self.assertLessEqual(prediction["model_score"], 1.0)
        self.assertIn(prediction["predicted_class_at_selected_development_threshold"], (0, 1))
        self.assertAlmostEqual(prediction["decision_threshold"], 0.6683593258453616, places=12)
        self.assertIn("not a calibrated flood probability", prediction["score_interpretation"])


if __name__ == "__main__":
    unittest.main()