import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.swmm_adapter import SwmmAdapter


class SwmmAdapterUnitTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.adapter = SwmmAdapter()

    def test_adapter_availability_and_status(self):
        status = self.adapter.get_status()
        self.assertTrue(status["pyswmm_available"])
        self.assertIn("5.2", str(status["swmm_engine_version"]))
        self.assertTrue(status["benchmark_model_ready"])
        self.assertFalse(status["mumbai_calibrated_model_available"])
        self.assertEqual(status["status"], "operational_benchmark_only")
        self.assertGreater(len(status["missing_prerequisites"]), 0)
        self.assertIn("synthetic benchmark", status["disclaimer"])

    def test_benchmark_model_run_and_mass_conservation(self):
        result = self.adapter.run_model(sample_interval_seconds=900)
        self.assertTrue(result["is_synthetic_benchmark"])
        self.assertEqual(result["flow_units"], "CMS")
        self.assertGreater(result["total_steps_simulated"], 100)

        # Continuity error verification (EPA SWMM threshold < 1.0%)
        continuity = result["continuity"]
        self.assertLess(abs(continuity["flow_routing_error_percent"]), 1.0)
        self.assertLess(abs(continuity["runoff_error_percent"]), 1.0)
        self.assertTrue(continuity["mass_balance_acceptable"])

        # System and node metrics
        nodes = result["nodes"]
        self.assertIn("J1", nodes)
        self.assertIn("J2", nodes)
        self.assertIn("O1", nodes)
        self.assertTrue(nodes["O1"]["is_outfall"])
        self.assertTrue(nodes["J1"]["is_junction"])

        # Links
        links = result["links"]
        self.assertIn("C1", links)
        self.assertIn("C2", links)
        self.assertGreater(links["C1"]["peak_flow_cms"], 0.0)

        # Snapshots
        self.assertGreater(len(result["snapshots"]), 0)

    def test_adapter_raises_on_missing_inp_file(self):
        with self.assertRaises(FileNotFoundError):
            self.adapter.run_model(inp_path="non_existent_directory/missing_model.inp")

    def test_swmm_status_endpoint(self):
        response = self.client.get("/api/v1/swmm/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["pyswmm_available"])
        self.assertFalse(data["mumbai_calibrated_model_available"])
        self.assertIn("benchmark", data["disclaimer"])

    def test_swmm_sample_run_endpoint(self):
        response = self.client.post("/api/v1/swmm/sample-run", json={"sample_interval_seconds": 900})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_synthetic_benchmark"])
        self.assertIn("nodes", data)
        self.assertIn("continuity", data)
        self.assertLess(abs(data["continuity"]["flow_routing_error_percent"]), 1.0)

    def test_swmm_sample_run_endpoint_missing_file_returns_404(self):
        response = self.client.post("/api/v1/swmm/sample-run", json={"inp_path": "invalid_path.inp"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["error"], "swmm_model_not_found")


if __name__ == "__main__":
    unittest.main()
