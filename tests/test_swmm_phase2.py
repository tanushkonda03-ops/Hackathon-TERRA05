from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, box

import backend.main as backend_main
from backend.main import app
from backend.swmm_physics import (
    SwmmPhysicsService,
    SwmmScenario,
    extract_node_flood_events,
    make_scaled_inp,
    nearest_object_mapping,
    read_rainfall_profile,
    read_water_balance,
    scenario_hash,
)


class Phase2ScenarioTests(unittest.TestCase):
    def test_hash_is_deterministic_and_uses_simulation_inputs_not_display_name(self):
        a = SwmmScenario("historical_2005", 1.0)
        b = SwmmScenario("rainfall_100", 1.0)
        self.assertEqual(scenario_hash(a), scenario_hash(b))
        self.assertNotEqual(scenario_hash(a), scenario_hash(SwmmScenario("rainfall_050", .5)))

    def test_rainfall_multiplier_scales_profile_and_preserves_source_model(self):
        original_sum = sum(row[2] for row in read_rainfall_profile())
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "scaled.inp"
            make_scaled_inp(SwmmScenario("rainfall_050", .5), dest)
            scaled_sum = sum(row[2] for row in read_rainfall_profile(dest))
            self.assertAlmostEqual(scaled_sum, original_sum * .5, places=3)
            self.assertEqual(len(read_rainfall_profile()), 108)

    def test_custom_rainfall_profile_is_padded_and_volume_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "custom.inp"
            make_scaled_inp(SwmmScenario("custom_event", .5, rainfall_profile_mm=(4.0, 6.0)), dest)
            values = [row[2] for row in read_rainfall_profile(dest)]
            self.assertAlmostEqual(sum(values), 5.0)
            self.assertAlmostEqual(values[0], 2.0)
            self.assertAlmostEqual(values[1], 3.0)
            self.assertEqual(sum(values[2:]), 0.0)

    def test_node_event_preserves_timestamps_peak_and_flood_duration(self):
        series = pd.DataFrame([
            {"node_id": "N1", "timestamp": "2005-07-26T00:00:00", "node_depth_m": .2, "node_flooding_rate_m3s": 0., "node_flooding_m3": 0.},
            {"node_id": "N1", "timestamp": "2005-07-26T00:15:00", "node_depth_m": .5, "node_flooding_rate_m3s": .1, "node_flooding_m3": 90.},
            {"node_id": "N1", "timestamp": "2005-07-26T00:30:00", "node_depth_m": .7, "node_flooding_rate_m3s": .2, "node_flooding_m3": 180.},
        ])
        event = extract_node_flood_events(series)[0]
        self.assertEqual(event["first_flood_time"], "2005-07-26T00:15:00")
        self.assertEqual(event["peak_flood_time"], "2005-07-26T00:30:00")
        self.assertEqual(event["flood_duration_minutes"], 30)
        self.assertEqual(event["peak_depth_m"], .7)
        self.assertEqual(event["total_flood_volume_m3"], 270)
        self.assertIsNone(event["surface_depth_m"])

    def test_water_balance_keeps_runoff_and_drainage_inflow_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            rpt = Path(temp) / "fixture.rpt"
            rpt.write_text("""
Total Precipitation ...... 100.0 50.0
Infiltration Loss ......... 20.0 10.0
Surface Runoff ........... 70.0 35.0
Wet Weather Inflow ....... 70.0 700.0
External Outflow ......... 60.0 600.0
Flooding Loss ............ 5.0 50.0
Final Stored Volume ...... 5.0 50.0
Continuity Error (%) ...... -0.1
""")
            balance = read_water_balance(rpt)
            self.assertEqual(balance["rainfall_volume_ML"], 1000.0)
            self.assertEqual(balance["surface_runoff_volume_ML"], 700.0)
            self.assertEqual(balance["drainage_inflow_ML"], 700.0)
            self.assertNotEqual(balance["surface_runoff_volume_ML"], balance["drainage_inflow_ML"] * 2)
            self.assertIsNone(balance["surface_storage_ML"])

    def test_node_conduit_and_subcatchment_nearest_grid_mappings(self):
        grid = gpd.GeoDataFrame({"grid_id": [1, 2]}, geometry=[Point(0, 0), Point(10, 0)], crs="EPSG:32643")
        cases = [
            (gpd.GeoDataFrame({"node_id": ["n1", "n2"]}, geometry=[Point(1, 0), Point(11, 0)], crs=grid.crs), "node_id", "nearest_node", "node_distance_m"),
            (gpd.GeoDataFrame({"conduit_id": ["c1", "c2"]}, geometry=[LineString([(1, -1), (1, 1)]), LineString([(11, -1), (11, 1)])], crs=grid.crs), "conduit_id", "nearest_conduit", "conduit_distance_m"),
            (gpd.GeoDataFrame({"subcatchment_id": ["s1", "s2"]}, geometry=[box(-1, -1, 2, 1), box(9, -1, 12, 1)], crs=grid.crs), "subcatchment_id", "nearest_subcatchment", "subcatchment_distance_m"),
        ]
        for assets, id_col, output_id, distance_col in cases:
            mapped = nearest_object_mapping(grid, assets, id_col, output_id, distance_col)
            self.assertEqual(len(mapped), 2)
            self.assertTrue(mapped[distance_col].max() >= 0)
            self.assertTrue(mapped[output_id].notna().all())

    def test_cached_identical_scenario_is_not_requeued(self):
        with tempfile.TemporaryDirectory() as temp:
            service = SwmmPhysicsService(Path(temp))

            def complete(scenario, simulation_id, digest):
                path = service._job_path(simulation_id)
                record = json.loads(path.read_text())
                record.update(status="completed", summary={"max_node_depth_m": 1.0})
                path.write_text(json.dumps(record))

            service._run_job = complete
            first = service.submit(SwmmScenario("historical_2005", 1.0))
            service._futures[first["simulation_id"]].result(timeout=5)
            second = service.submit(SwmmScenario("rainfall_100", 1.0))
            self.assertEqual(first["simulation_id"], second["simulation_id"])
            self.assertTrue(second["cache_hit"])
            service._executor.shutdown(wait=True)


class Phase2ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original = backend_main.swmm_physics_service

    def tearDown(self):
        backend_main.swmm_physics_service = self.original

    def test_submit_status_and_result_retrieval_api(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "node_physics_timeseries.csv"
            csv_path.write_text("timestamp,node_id\n2005-07-26T00:00:00,N1\n")

            class FakeService:
                def submit(self, scenario):
                    scenario.validate()
                    return {"simulation_id": "sim_0123456789abcdefabcd", "scenario_id": scenario.scenario_id,
                            "status": "queued", "cache_hit": False, "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"}

                def status(self, simulation_id):
                    return {"simulation_id": simulation_id, "scenario_id": "historical_2005", "status": "completed",
                            "cache_hit": True, "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"}

                def results(self, simulation_id, table):
                    return csv_path

            backend_main.swmm_physics_service = FakeService()
            submitted = self.client.post("/api/v1/simulation/swmm", json={"scenario_id": "historical_2005", "rainfall_multiplier": 1.0})
            self.assertEqual(submitted.status_code, 202)
            sim_id = submitted.json()["simulation_id"]
            self.assertEqual(self.client.get(f"/api/v1/simulation/swmm/{sim_id}").json()["status"], "completed")
            result = self.client.get(f"/api/v1/simulation/swmm/{sim_id}/results/node_physics_timeseries.csv")
            self.assertEqual(result.status_code, 200)
            self.assertIn("node_id", result.text)

    def test_swmm_scenario_rejects_unsupported_tide(self):
        response = self.client.post("/api/v1/simulation/swmm", json={"tide_mode": "high"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
