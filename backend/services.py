from __future__ import annotations

import csv
import json
import logging
from functools import cached_property
from pathlib import Path
from typing import Any

from .config import Settings

LOGGER = logging.getLogger(__name__)


class BackendDataService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @cached_property
    def rainfall_rows(self) -> list[dict[str, Any]]:
        with self.settings.rainfall_catalog_path.open(newline="", encoding="utf-8") as handle:
            return [
                {
                    **row,
                    "rainfall_15min_mm": float(row["rainfall_15min_mm"]),
                    "intensity_mm_per_hr": float(row["intensity_mm_per_hr"]),
                }
                for row in csv.DictReader(handle)
            ]

    @cached_property
    def rainfall_metadata(self) -> dict[str, Any]:
        return json.loads(self.settings.rainfall_metadata_path.read_text(encoding="utf-8"))

    @cached_property
    def drainage_network(self) -> dict[str, Any]:
        drainage_path = self.settings.root / "data" / "processed" / "bmc_storm_water_drains_working.geojson"
        return json.loads(drainage_path.read_text(encoding="utf-8"))

    def scenarios(self) -> list[dict[str, Any]]:
        metadata = self.rainfall_metadata
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in self.rainfall_rows:
            grouped.setdefault(row["timeseries_id"], []).append(row)
        result = []
        for series_id, details in metadata["scenarios"].items():
            rows = grouped.get(series_id, [])
            validation = metadata.get("validation", {})
            peak_result = validation.get("peak_scenarios", {}).get(series_id, {})
            depth_result = validation.get("depth_scenarios", {}).get(series_id, {})
            result.append({
                "timeseries_id": series_id,
                "family": details["family"],
                "classification": details["classification"],
                "interval_minutes": metadata["interval_minutes"],
                "duration_hours": metadata["scenario_duration_hours"] if series_id != "TS_2005_JULY26" else len(rows) * metadata["interval_minutes"] / 60,
                "record_count": len(rows),
                "total_depth_mm": round(sum(row["rainfall_15min_mm"] for row in rows), 6),
                "peak_intensity_mm_per_hr": round(max((row["intensity_mm_per_hr"] for row in rows), default=0), 6),
                "units": metadata["units"],
                "validation_status": "validated" if peak_result or depth_result or series_id == "TS_2005_JULY26" else "metadata_only",
                "intervals": rows,
            })
        return result

    @cached_property
    def feature_table(self):
        import pandas as pd
        return pd.read_csv(self.settings.ml_features_path)

    @cached_property
    def model(self):
        import joblib
        return joblib.load(self.settings.model_path)

    def model_prediction(self, grid_id: int) -> tuple[float, dict[str, Any]]:
        import pandas as pd

        table = self.feature_table
        matches = table[table["grid_id"] == grid_id]
        if matches.empty:
            raise LookupError(f"No ML feature row exists for grid_id {grid_id}")
        model = self.model
        feature_names = list(getattr(model, "feature_names_in_", []))
        if not feature_names:
            raise RuntimeError("Saved model does not expose feature_names_in_")
        missing = [name for name in feature_names if name not in matches.columns]
        if missing:
            raise RuntimeError(f"Required model features are unavailable: {missing}")
        row = matches.iloc[[0]]
        score = float(model.predict_proba(row[feature_names])[0, 1])
        return score, {"grid_id": int(row.iloc[0]["grid_id"]), "ward": str(row.iloc[0]["ward"])}

    def grid_id_for_coordinates(self, latitude: float, longitude: float) -> int:
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError as exc:
            raise RuntimeError("Coordinate lookup requires GeoPandas and Shapely") from exc
        grid = gpd.read_file(self.settings.risk_grid_path)
        if grid.crs is None:
            raise RuntimeError("Risk grid has no CRS")
        point = gpd.GeoSeries([Point(longitude, latitude)], crs="EPSG:4326").to_crs(grid.crs).iloc[0]
        matches = grid[grid.geometry.contains(point) | grid.geometry.touches(point)]
        if matches.empty:
            raise LookupError("Coordinates do not fall inside the supported Mumbai risk grid")
        return int(matches.iloc[0]["grid_id"])

    @cached_property
    def risk_geojson(self) -> dict[str, Any]:
        return json.loads(self.settings.risk_grid_path.read_text(encoding="utf-8"))

    @staticmethod
    def _geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
        coordinates = geometry.get("coordinates", [])
        values: list[tuple[float, float]] = []
        def visit(value: Any) -> None:
            if isinstance(value, (list, tuple)) and len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
                values.append((float(value[0]), float(value[1])))
            elif isinstance(value, (list, tuple)):
                for child in value:
                    visit(child)
        visit(coordinates)
        if not values:
            return (0, 0, 0, 0)
        xs, ys = zip(*values)
        return min(xs), min(ys), max(xs), max(ys)

    def risk_features(self, offset: int, limit: int, bbox: tuple[float, float, float, float] | None) -> tuple[list[dict[str, Any]], int]:
        features = self.risk_geojson.get("features", [])
        if bbox:
            minx, miny, maxx, maxy = bbox
            features = [
                feature for feature in features
                if not (
                    self._geometry_bbox(feature.get("geometry", {}))[2] < minx
                    or self._geometry_bbox(feature.get("geometry", {}))[0] > maxx
                    or self._geometry_bbox(feature.get("geometry", {}))[3] < miny
                    or self._geometry_bbox(feature.get("geometry", {}))[1] > maxy
                )
            ]
        total = len(features)
        return features[offset:offset + limit], total

    @cached_property
    def swmm_adapter(self):
        from .swmm_adapter import SwmmAdapter
        return SwmmAdapter()

    def swmm_status(self) -> dict[str, Any]:
        return self.swmm_adapter.get_status()

    def run_swmm(
        self,
        inp_path: str | Path | None = None,
        sample_interval_seconds: int = 900,
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        return self.swmm_adapter.run_model(
            inp_path=inp_path,
            sample_interval_seconds=sample_interval_seconds,
            max_steps=max_steps,
        )

    def status(self) -> dict[str, Any]:
        def component(path: Path, detail: str) -> dict[str, Any]:
            return {"ready": path.is_file(), "path": str(path), "detail": detail if path.is_file() else f"Missing: {path}"}
        swmm_stat = self.swmm_status()
        swmm_detail = (
            f"PySWMM v{swmm_stat.get('pyswmm_version')} (SWMM {swmm_stat.get('swmm_engine_version')}) ready with synthetic benchmark; "
            "no calibrated Mumbai municipal .inp model available"
            if swmm_stat.get("pyswmm_available")
            else "PySWMM is not installed"
        )
        return {
            "api": "ready",
            "model": component(self.settings.model_path, "Saved susceptibility model artifact available; load occurs on first prediction"),
            "rainfall_catalogue": component(self.settings.rainfall_catalog_path, "Validated rainfall catalogue available"),
            "geospatial_data": component(self.settings.risk_grid_path, "100 m flood grid GeoJSON available"),
            "swmm_model": {
                "ready": False,
                "path": swmm_stat.get("benchmark_model_path"),
                "detail": swmm_detail,
            },
        }

    def run_simulation(
        self,
        scenario_id: str,
        ward: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        routing_enabled: bool = True,
        drainage_capacity_mm_hr: float = 25.0,
        max_timesteps: int | None = None,
        custom_duration_hours: float | None = None,
        custom_total_depth_mm: float | None = None,
    ) -> dict[str, Any]:
        from .simulation import SurfaceRunoffEngine

        metadata = self.rainfall_metadata
        if scenario_id == "CUSTOM":
            if custom_duration_hours is None or custom_total_depth_mm is None:
                raise ValueError("Custom rainfall requires duration and total depth")
            interval_minutes = int(metadata.get("interval_minutes", 15))
            interval_count = round(custom_duration_hours * 60 / interval_minutes)
            if interval_count < 1 or interval_count > 672:
                raise ValueError("Custom rainfall duration must produce between 1 and 672 intervals")
            interval_depth_mm = custom_total_depth_mm / interval_count
            intervals = [
                {
                    "timeseries_id": "CUSTOM",
                    "datetime": f"T+{index * interval_minutes}m",
                    "rainfall_15min_mm": interval_depth_mm,
                    "intensity_mm_per_hr": interval_depth_mm * 60 / interval_minutes,
                }
                for index in range(interval_count)
            ]
            scenario_info = {
                "family": "custom",
                "classification": "user-entered evenly distributed rainfall",
            }
        elif scenario_id not in metadata.get("scenarios", {}):
            valid_ids = list(metadata.get("scenarios", {}).keys())
            raise LookupError(f"Scenario '{scenario_id}' not found in catalogue. Valid scenarios: {valid_ids}")
        else:
            scenario_info = metadata["scenarios"][scenario_id]
            intervals = [row for row in self.rainfall_rows if row["timeseries_id"] == scenario_id]
            if not intervals:
                raise LookupError(f"No rainfall intervals found for scenario '{scenario_id}'")

        def _normalize_ward(w: str) -> str:
            w_clean = w.strip().upper().replace(" WARD", "").replace("WARD ", "").replace("WARD", "")
            mapping = {
                "F-SOUTH": "F/S", "F SOUTH": "F/S", "FS": "F/S", "DADAR": "F/S", "HINDMATA": "F/S",
                "F-NORTH": "F/N", "F NORTH": "F/N", "FN": "F/N", "SION": "F/N", "MATUNGA": "F/N",
                "G-NORTH": "G/N", "G NORTH": "G/N", "GN": "G/N", "DHARAVI": "G/N", "MAHIM": "G/N",
                "G-SOUTH": "G/S", "G SOUTH": "G/S", "GS": "G/S", "WORLI": "G/S", "LOWER PAREL": "G/S",
                "H-WEST": "H/W", "H WEST": "H/W", "HW": "H/W", "BANDRA WEST": "H/W", "KHAR": "H/W", "SANTACRUZ WEST": "H/W", "MILAN SUBWAY": "H/W",
                "H-EAST": "H/E", "H EAST": "H/E", "HE": "H/E", "BKC": "H/E", "BANDRA EAST": "H/E", "KALANAGAR": "H/E",
                "K-WEST": "K/W", "K WEST": "K/W", "KW": "K/W", "ANDHERI WEST": "K/W", "ANDHERI SUBWAY": "K/W", "JUHU": "K/W", "VERSOVA": "K/W",
                "K-EAST": "K/E", "K EAST": "K/E", "KE": "K/E", "ANDHERI EAST": "K/E", "SAKI NAKA": "K/E",
                "M-WEST": "M/W", "M WEST": "M/W", "MW": "M/W", "CHEMBUR": "M/W", "AMAR MAHAL": "M/W",
                "M-EAST": "M/E", "M EAST": "M/E", "ME": "M/E", "GOVANDI": "M/E", "MANKHURD": "M/E",
                "P-NORTH": "P/N", "P NORTH": "P/N", "PN": "P/N", "MALAD": "P/N", "MALAD SUBWAY": "P/N",
                "P-SOUTH": "P/S", "P SOUTH": "P/S", "PS": "P/S", "GOREGAON": "P/S",
                "R-NORTH": "R/N", "R NORTH": "R/N", "RN": "R/N", "DAHISAR": "R/N",
                "R-SOUTH": "R/S", "R SOUTH": "R/S", "RS": "R/S", "KANDIVALI": "R/S",
                "R-CENTRAL": "R/C", "R CENTRAL": "R/C", "RC": "R/C", "BORIVALI": "R/C",
                "L": "L", "KURLA": "L", "KALINA": "L",
                "N": "N", "GHATKOPAR": "N",
                "S": "S", "BHANDUP": "S", "POWAI": "S",
                "T": "T", "MULUND": "T",
            }
            return mapping.get(w_clean, w_clean)

        features = self.risk_geojson.get("features", [])
        if ward:
            norm_ward = _normalize_ward(ward)
            features = [f for f in features if str(f.get("properties", {}).get("ward", "")).upper() == norm_ward.upper()]
        elif bbox:
            minx, miny, maxx, maxy = bbox
            features = [
                f for f in features
                if not (
                    self._geometry_bbox(f.get("geometry", {}))[2] < minx
                    or self._geometry_bbox(f.get("geometry", {}))[0] > maxx
                    or self._geometry_bbox(f.get("geometry", {}))[3] < miny
                    or self._geometry_bbox(f.get("geometry", {}))[1] > maxy
                )
            ]
        else:
            # Default to Ward L (Mithi River Basin Kurla/Kalina pilot catchment corridor)
            features = [f for f in features if str(f.get("properties", {}).get("ward", "")).upper() == "L"]

        if not features:
            target_desc = f"ward '{ward}'" if ward else f"bbox {bbox}" if bbox else "default corridor (Ward L)"
            raise LookupError(f"No spatial grid cells found for {target_desc}")

        engine = SurfaceRunoffEngine(
            features=features,
            scenario_intervals=intervals,
            scenario_id=scenario_id,
            scenario_metadata=scenario_info,
            routing_enabled=routing_enabled,
            drainage_capacity_mm_hr=drainage_capacity_mm_hr,
            max_timesteps=max_timesteps,
        )
        return engine.run()
