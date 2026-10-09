import unittest
from pathlib import Path

import pandas as pd

from scripts.swmm_phase1 import classify_slope, raw_slope, safe_id, SWMM_SHAPES


class SwmmPhase1HelpersTest(unittest.TestCase):
    def test_identifier_is_safe_deterministic_and_collision_resistant(self):
        a = safe_id("N", "2175076802!!!")
        self.assertEqual(a, safe_id("N", "2175076802!!!"))
        self.assertLessEqual(len(a), 31)
        self.assertTrue(a.replace("_", "").isalnum())
        self.assertNotEqual(a, safe_id("N", "2175076802"))

    def test_raw_slope_is_not_floored(self):
        self.assertAlmostEqual(raw_slope(10.0, 12.0, 100.0), -0.02)
        self.assertEqual(raw_slope(10.0, 10.0, 100.0), 0.0)
        self.assertIsNone(raw_slope(10.0, 9.0, 0.0))
        self.assertEqual(classify_slope(-0.02), "negative")
        self.assertEqual(classify_slope(0.0), "near-zero")
        self.assertEqual(classify_slope(None), "undefined")

    def test_shape_table_is_explicit(self):
        self.assertEqual(SWMM_SHAPES["CIRC"][0], "CIRCULAR")
        self.assertEqual(SWMM_SHAPES["OREC"][0], "RECT_OPEN")
        self.assertIn("ASSUMED", SWMM_SHAPES["OREC"][1])
        self.assertNotIn("UNKNOWN", SWMM_SHAPES)

    def test_historical_rainfall_reconciles(self):
        path = Path(__file__).resolve().parents[1] / "data" / "swmm_ready" / "swmm_rainfall_catalog.csv"
        rain = pd.read_csv(path)
        event = rain.loc[rain.timeseries_id == "TS_2005_JULY26"]
        self.assertEqual(len(event), 108)
        self.assertAlmostEqual(float(event.rainfall_15min_mm.sum()), 944.2, places=2)


if __name__ == "__main__":
    unittest.main()
