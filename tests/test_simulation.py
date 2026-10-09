import unittest
from fastapi.testclient import TestClient

from backend.main import app
import backend.main as backend_main
from backend.simulation import SurfaceRunoffEngine, utm43_to_wgs84


class SimulationEngineUnitTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_utm43_to_wgs84_accuracy(self):
        # Known Kurla point: UTM Zone 43N [276903.2, 2110188.3] -> Mumbai [~19.0724, ~72.8798]
        lat, lon = utm43_to_wgs84(276903.2, 2110188.3)
        self.assertAlmostEqual(lat, 19.0724, places=3)
        self.assertAlmostEqual(lon, 72.8798, places=3)

    def test_simulation_endpoint_success_and_schema(self):
        payload = {
            "scenario_id": "DESIGN_RED_100MM",
            "ward": "L",
            "routing_enabled": True,
            "drainage_capacity_mm_hr": 25.0
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["scenario_id"], "DESIGN_RED_100MM")
        self.assertEqual(data["interval_minutes"], 15)
        self.assertEqual(len(data["timesteps"]), 12)
        self.assertEqual(data["domain_summary"]["cell_count"], 1516)
        self.assertEqual(data["domain_summary"]["crs"], "EPSG:32643")

        # Verify mass conservation
        wb = data["water_balance"]
        self.assertGreater(wb["total_rainfall_volume_m3"], 0)
        self.assertGreater(wb["total_surface_storage_volume_m3"], 0)
        self.assertLess(wb["mass_balance_error_percent"], 0.01)

        # Verify per-cell results
        cells = data["cells"]
        self.assertEqual(len(cells), 1516)
        first_cell = cells[0]
        self.assertIn("grid_id", first_cell)
        self.assertIn("centroid_lat", first_cell)
        self.assertIn("centroid_lng", first_cell)
        self.assertEqual(len(first_cell["depth_by_timestep"]), 12)
        self.assertGreaterEqual(first_cell["max_depth_m"], 0.0)

        # Verify limitations
        self.assertGreater(len(data["limitations"]), 0)
        self.assertTrue(any("EPA-SWMM" in lim for lim in data["limitations"]))

    def test_simulation_without_routing(self):
        payload = {
            "scenario_id": "DESIGN_YELLOW_25MM",
            "ward": "L",
            "routing_enabled": False,
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("local storage", data["domain_summary"]["routing_method"])

    def test_simulation_max_timesteps_cutoff(self):
        payload = {
            "scenario_id": "DESIGN_ORANGE_50MM",
            "ward": "L",
            "max_timesteps": 4
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["timesteps"]), 4)
        self.assertEqual(len(data["cells"][0]["depth_by_timestep"]), 4)

    def test_simulation_rejects_unknown_scenario(self):
        payload = {
            "scenario_id": "NON_EXISTENT_SCENARIO",
            "ward": "L"
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["error"], "simulation_input_not_found")

    def test_simulation_rejects_empty_ward(self):
        payload = {
            "scenario_id": "DESIGN_RED_100MM",
            "ward": "NON_EXISTENT_WARD_XYZ"
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_simulation_rejects_invalid_drainage_parameter(self):
        payload = {
            "scenario_id": "DESIGN_RED_100MM",
            "drainage_capacity_mm_hr": -10.0
        }
        response = self.client.post("/api/v1/simulation/run", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_unit_conversions_consistent(self):
        # 100 mm/hr for 15 min = 25 mm depth
        # 25 mm depth on 10,000 m^2 (1 ha) = 250 m^3 volume
        intensity_mm_hr = 100.0
        interval_hr = 15.0 / 60.0
        depth_mm = intensity_mm_hr * interval_hr
        self.assertEqual(depth_mm, 25.0)

        area_m2 = 10000.0
        vol_m3 = (depth_mm / 1000.0) * area_m2
        self.assertEqual(vol_m3, 250.0)

    def test_analytical_single_cell_water_balance(self):
        # Synthetic single cell in UTM Zone 43N
        single_cell_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[276900, 2110100], [277000, 2110100], [277000, 2110200], [276900, 2110200], [276900, 2110100]]]
            },
            "properties": {
                "grid_id": 99999,
                "ward": "L",
                "elevation": 15.0,
                "slope": 1.2,
                "built_up_fraction": 0.5,
                "conduit_density_m_per_ha": 15.0,
                "clay_fraction": 0.25,
            }
        }
        intervals = [
            {"rainfall_15min_mm": 20.0, "intensity_mm_per_hr": 80.0, "datetime": "2026-07-26 00:00:00"},
            {"rainfall_15min_mm": 40.0, "intensity_mm_per_hr": 160.0, "datetime": "2026-07-26 00:15:00"},
            {"rainfall_15min_mm": 10.0, "intensity_mm_per_hr": 40.0, "datetime": "2026-07-26 00:30:00"},
            {"rainfall_15min_mm": 0.0, "intensity_mm_per_hr": 0.0, "datetime": "2026-07-26 00:45:00"},
        ]
        engine = SurfaceRunoffEngine(
            features=[single_cell_feature],
            scenario_intervals=intervals,
            scenario_id="ANALYTICAL_TEST",
            routing_enabled=False,
            drainage_capacity_mm_hr=20.0,
        )
        res = engine.run()
        wb = res["water_balance"]
        total_p = wb["total_rainfall_volume_m3"]
        total_infil = wb["total_infiltration_volume_m3"]
        total_depr = wb["total_depression_storage_volume_m3"]
        total_drain = wb["total_drainage_removed_volume_m3"]
        total_surf = wb["total_surface_storage_volume_m3"]

        # Exact conservation: P = Infil + Depr + Drain + Surf
        expected_p = (20.0 + 40.0 + 10.0 + 0.0) / 1000.0 * 10000.0  # 700 m^3
        self.assertAlmostEqual(total_p, expected_p, places=3)
        self.assertAlmostEqual(total_p, total_infil + total_depr + total_drain + total_surf, places=3)
        self.assertLess(wb["mass_balance_error_percent"], 0.0001)

    def test_downhill_routing_transfers_water(self):
        # Two adjacent cells: cell 1 (high elevation: 20m) and cell 2 (low elevation: 10m)
        cell_high = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[276900, 2110200], [277000, 2110200], [277000, 2110300], [276900, 2110300], [276900, 2110200]]]
            },
            "properties": {"grid_id": 1, "ward": "L", "elevation": 20.0, "slope": 5.0, "built_up_fraction": 1.0, "conduit_density_m_per_ha": 0.0}
        }
        cell_low = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[276900, 2110100], [277000, 2110100], [277000, 2110200], [276900, 2110200], [276900, 2110100]]]
            },
            "properties": {"grid_id": 2, "ward": "L", "elevation": 10.0, "slope": 0.5, "built_up_fraction": 1.0, "conduit_density_m_per_ha": 0.0}
        }
        intervals = [{"rainfall_15min_mm": 50.0, "intensity_mm_per_hr": 200.0}]

        # Without routing: both cells retain identical depth
        eng_no_route = SurfaceRunoffEngine(
            features=[cell_high, cell_low],
            scenario_intervals=intervals,
            scenario_id="TEST_NO_ROUTE",
            routing_enabled=False,
            drainage_capacity_mm_hr=0.0,
        )
        res_no_route = eng_no_route.run()
        d_high_noroute = res_no_route["cells"][0]["final_depth_m"]
        d_low_noroute = res_no_route["cells"][1]["final_depth_m"]
        self.assertAlmostEqual(d_high_noroute, d_low_noroute, places=3)

        # With routing: water flows from high cell to low cell
        eng_route = SurfaceRunoffEngine(
            features=[cell_high, cell_low],
            scenario_intervals=intervals,
            scenario_id="TEST_ROUTE",
            routing_enabled=True,
            drainage_capacity_mm_hr=0.0,
        )
        res_route = eng_route.run()
        d_high_route = res_route["cells"][0]["final_depth_m"]
        d_low_route = res_route["cells"][1]["final_depth_m"]

        # Water in high cell must be less than in low cell due to downhill gradient
        self.assertLess(d_high_route, d_low_route)


if __name__ == "__main__":
    unittest.main()

