import json
import unittest

from fastapi.testclient import TestClient

from backend.main import app
import backend.main as backend_main
from backend.services import BackendDataService


class BackendEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.original_service = backend_main.service

    @classmethod
    def tearDownClass(cls):
        backend_main.service = cls.original_service

    def test_health_and_system_status_report_independent_components(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["status"], {"ok", "degraded"})
        status = self.client.get("/api/v1/system-status")
        self.assertEqual(status.status_code, 200)
        payload = status.json()
        self.assertTrue(payload["rainfall_catalogue"]["ready"])
        self.assertTrue(payload["geospatial_data"]["ready"])
        self.assertEqual(payload["swmm_model"]["ready"], backend_main.service.swmm_status()["pyswmm_available"])

    def test_scenarios_match_validated_catalogue(self):
        response = self.client.get("/api/v1/scenarios")
        self.assertEqual(response.status_code, 200)
        scenarios = {scenario["timeseries_id"]: scenario for scenario in response.json()}
        self.assertEqual(len(scenarios), 9)
        self.assertEqual(scenarios["TS_2005_JULY26"]["record_count"], 108)
        self.assertAlmostEqual(scenarios["TS_2005_JULY26"]["total_depth_mm"], 944.2, places=2)
        self.assertAlmostEqual(scenarios["DESIGN_RED_100MM"]["peak_intensity_mm_per_hr"], 100.0, places=5)
        self.assertAlmostEqual(scenarios["DEPTH_50MM_3H"]["total_depth_mm"], 50.0, places=5)
        self.assertEqual(len(scenarios["DEPTH_150MM_3H"]["intervals"]), 12)

    def test_risk_map_pagination_and_invalid_bbox(self):
        response = self.client.get("/api/v1/risk-map?offset=1&limit=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["returned"], 2)
        self.assertEqual(response.json()["type"], "FeatureCollection")
        invalid = self.client.get("/api/v1/risk-map?minx=1&miny=2")
        self.assertEqual(invalid.status_code, 422)

    def test_predict_rejects_invalid_location(self):
        response = self.client.post("/api/v1/predict", json={})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/api/v1/predict", json={"grid_id": 1, "latitude": 19.1, "longitude": 72.9})
        self.assertEqual(response.status_code, 422)

    def test_predict_reports_unavailable_phase3_model_without_fabricating_score(self):
        original_ml_service = backend_main.phase3_ml_service

        class UnavailablePhase3Model:
            def predict(self, grid_id, scenario_id="historical_2005"):
                raise ImportError("model artifact unavailable")

        try:
            backend_main.phase3_ml_service = UnavailablePhase3Model()
            response = self.client.post("/api/v1/predict", json={"grid_id": 1})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"]["error"], "susceptibility_model_unavailable")
        finally:
            backend_main.phase3_ml_service = original_ml_service


if __name__ == "__main__":
    unittest.main()
