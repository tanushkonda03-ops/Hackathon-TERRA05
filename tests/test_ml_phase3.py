import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from xgboost import XGBClassifier

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "data" / "ml_phase3"


class Phase3DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master = pd.read_csv(PHASE3 / "datasets" / "training_master.csv", low_memory=False)
        cls.supported = pd.read_csv(PHASE3 / "datasets" / "physics_supported_master.csv", low_memory=False)
        cls.schema = json.loads((PHASE3 / "models" / "feature_schema.json").read_text(encoding="utf-8"))
        cls.metadata = json.loads((PHASE3 / "models" / "terra05_xgb_metadata.json").read_text(encoding="utf-8"))

    def test_targets_and_grid_join_are_valid(self):
        self.assertEqual(len(self.master), 47758)
        self.assertEqual(self.master.grid_id.nunique(), len(self.master))
        self.assertEqual(int(self.master.flood_label.sum()), 1953)
        self.assertFalse(self.master.flood_label.isna().any())
        self.assertTrue(self.master.flood_fraction.between(0, 1).all())
        self.assertEqual(len(self.supported), 1516)

    def test_target_leakage_fields_are_not_predictors(self):
        predictors = set(self.schema["features"])
        self.assertTrue(predictors.isdisjoint({"flood_label", "flood_fraction", "historical_flood_fraction", "historical_flood_overlap"}))
        self.assertNotIn("spatial_cv_fold", predictors)
        self.assertNotIn("mapping_classification", predictors)

    def test_uncovered_physics_remains_missing_and_is_flagged(self):
        uncovered = self.master[self.master.physics_coverage.eq(0)]
        self.assertEqual(len(uncovered), 46242)
        self.assertTrue(uncovered.swmm_nearest_node_depth_proxy_m.isna().all())
        self.assertTrue(self.master.loc[self.master.physics_coverage.eq(1), "swmm_nearest_node_depth_proxy_m"].notna().any())

    def test_spatial_partitions_have_no_shared_blocks_and_both_classes(self):
        splits = self.metadata["spatial_groups"]
        self.assertFalse(set(splits["train"]) & set(splits["validation"]))
        self.assertFalse(set(splits["train"]) & set(splits["test"]))
        self.assertFalse(set(splits["validation"]) & set(splits["test"]))
        for partition in ("train", "validation", "test"):
            self.assertGreater(self.metadata["split_counts"][partition]["positive"], 1)

    def test_model_serialization_roundtrip(self):
        X = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
        y = np.array([0, 0, 0, 1, 1, 1])
        model = XGBClassifier(n_estimators=8, max_depth=1, n_jobs=1, random_state=42, eval_metric="aucpr")
        model.fit(X, y)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roundtrip.json"
            model.save_model(path)
            loaded = XGBClassifier()
            loaded.load_model(path)
            np.testing.assert_allclose(model.predict_proba(X), loaded.predict_proba(X))


class Phase3ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_predict_returns_supported_physics_provenance(self):
        response = self.client.post("/api/v1/ml/predict", json={"grid_id": 22963})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["physics_supported"])
        self.assertEqual(payload["prediction_mode"], "physics_supported")
        self.assertEqual(payload["model_version"], "terra05-xgb-v1.0.0")
        self.assertIn("risk_score", payload)
        self.assertIn("risk_level", payload)

    def test_predict_uses_gis_only_outside_physics_domain(self):
        response = self.client.post("/api/v1/ml/predict", json={"grid_id": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["physics_supported"])
        self.assertEqual(response.json()["prediction_mode"], "citywide_gis_only")
        self.assertIsNone(response.json()["predicted_label"])

    def test_other_scenario_rejected_without_matched_labels(self):
        response = self.client.post("/api/v1/ml/predict", json={"grid_id": 22963, "scenario_id": "rainfall_050"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
