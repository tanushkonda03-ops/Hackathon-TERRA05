import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ScenarioRunRequest

ROOT = Path(__file__).resolve().parents[1]


class Phase4AuditTests(unittest.TestCase):
    def test_registry_records_five_events_and_no_supervised_eligibility(self):
        import pandas as pd
        registry = pd.read_csv(ROOT / "data/ml_phase4/datasets/event_registry.csv")
        self.assertEqual(set(registry.event_id), {"E001", "E002", "E003", "E004", "E005"})
        self.assertFalse(registry.event_matched_target.any())
        self.assertEqual(len(pd.read_csv(ROOT / "data/ml_phase4/datasets/train.csv")), 0)

    def test_candidate_dataset_event_grid_integrity(self):
        import pandas as pd
        path = ROOT / "data/ml_phase4/datasets/multi_event_master.csv"
        data = pd.read_csv(path, low_memory=False)
        self.assertEqual(data.duplicated(["event_id", "grid_id"]).sum(), 0)
        self.assertEqual(data.event_target_eligibility.nunique(), 1)
        self.assertEqual(data.event_target_eligibility.iloc[0], "INSUFFICIENT_PROVENANCE")
        self.assertFalse(data.event_target_match_verified.any())


class Phase4ScenarioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_manual_custom_and_historical_contract(self):
        custom = ScenarioRunRequest(mode="custom", total_rainfall_mm=150, duration_minutes=360)
        self.assertEqual(custom.mode, "custom")
        historical = ScenarioRunRequest(mode="historical_replay", event_id="E001")
        self.assertEqual(historical.event_id, "E001")

    def test_invalid_rainfall_is_rejected(self):
        for data in (
            {"mode": "custom"},
            {"mode": "custom", "total_rainfall_mm": 10, "duration_minutes": 17},
            {"mode": "historical_replay", "event_id": "E003"},
            {"mode": "custom", "profile_mm": [1, -1]},
        ):
            with self.subTest(data=data), self.assertRaises(Exception):
                ScenarioRunRequest(**data)

    def test_unknown_status_and_results_return_404(self):
        self.assertEqual(self.client.get("/api/v1/scenario/scn_00000000000000000000").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/scenario/scn_00000000000000000000/results").status_code, 404)

    def test_unfinished_scenario_results_return_conflict(self):
        phase = ROOT / "data/ml_phase4/scenarios/jobs"
        phase.mkdir(parents=True, exist_ok=True)
        (phase / "scn_11111111111111111111.json").write_text(json.dumps({"simulation_id": "scn_11111111111111111111", "status": "RUNNING"}), encoding="utf-8")
        try:
            self.assertEqual(self.client.get("/api/v1/scenario/scn_11111111111111111111/results").status_code, 409)
        finally:
            (phase / "scn_11111111111111111111.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
