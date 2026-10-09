"""Phase 4 asynchronous rainfall -> SWMM -> ML scenario orchestration."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

import pandas as pd
import numpy as np
from xgboost import XGBClassifier

from .ml_service import Phase3MLService
from .swmm_physics import SwmmPhysicsService, SwmmScenario

LOGGER = logging.getLogger(__name__)


class RainfallProvider(Protocol):
    """Adapter contract for a configured external source; input is normalized mm/15 min."""
    provider_name: str

    def fetch_profile_mm(self) -> Sequence[float]: ...


class ScenarioService:
    def __init__(self, root: Path, physics: SwmmPhysicsService, ml: Phase3MLService):
        self.root = root
        self.physics = physics
        self.ml = ml
        self.directory = root / "data" / "ml_phase4" / "scenarios"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.jobs = self.directory / "jobs"
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.results_dir = root / "data" / "ml_phase4" / "predictions" / "scenario_predictions"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="terra05-scenario")
        self.lock = threading.Lock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _path(self, simulation_id: str) -> Path:
        if not simulation_id.startswith("scn_") or len(simulation_id) != 24:
            raise LookupError("Unknown scenario id")
        return self.jobs / f"{simulation_id}.json"

    def submit(self, request: dict[str, Any]) -> dict[str, Any]:
        mode = request["mode"]
        profile = request.get("profile_mm")
        source = "user-defined scenario"
        event_id = None
        if mode == "historical_replay":
            if request.get("event_id") != "E001":
                raise ValueError("Only E001 has a runnable historical SWMM rainfall profile")
            from .swmm_physics import read_rainfall_profile
            profile = [row[2] for row in read_rainfall_profile()]
            source, event_id = "historical dataset; reconstructed 15-minute profile", "E001"
        elif profile is None:
            duration = int(request["duration_minutes"])
            intervals = duration // 15
            profile = [float(request["total_rainfall_mm"]) / intervals] * intervals
        if not profile or len(profile) > 108 or len(profile) * 15 > 1620:
            raise ValueError("Rainfall profile must contain 1 to 108 fifteen-minute depths")
        if any(not math.isfinite(float(value)) or float(value) < 0 for value in profile):
            raise ValueError("Rainfall profile values must be finite, non-negative millimetres")
        if mode != "historical_replay" and (len(profile) * 15) % 15:
            raise ValueError("Rainfall duration must be in 15-minute intervals")
        rainfall_hash = hashlib.sha256(json.dumps([round(float(x), 8) for x in profile], separators=(",", ":")).encode()).hexdigest()
        scenario_id = "historical_2005" if mode == "historical_replay" else f"custom_{rainfall_hash[:12]}"
        payload = {"mode": mode, "event_id": event_id, "scenario_id": scenario_id, "rainfall_hash": rainfall_hash,
                   "rainfall_total_mm": sum(profile), "duration_minutes": len(profile) * 15, "profile_mm": profile, "rainfall_source": source,
                   "orchestrator_version": "terra05-phase4-v4-eager-ml-imports"}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        simulation_id = f"scn_{digest[:20]}"
        path = self._path(simulation_id)
        with self.lock:
            if path.is_file():
                record = json.loads(path.read_text(encoding="utf-8"))
                record["cache_hit"] = True
                return record
            record = {"simulation_id": simulation_id, "scenario_id": scenario_id, "mode": mode, "event_id": event_id,
                      "status": "QUEUED", "cache_hit": False, "created_at": self._now(), "updated_at": self._now(),
                      "rainfall_source": source, "rainfall_hash": rainfall_hash, "rainfall_total_mm": payload["rainfall_total_mm"],
                      "duration_minutes": payload["duration_minutes"], "physics_supported": False,
                      "prediction_mode": "PENDING", "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"}
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            self.executor.submit(self._run, path, payload)
        return record

    def _update(self, path: Path, **values: Any) -> dict[str, Any]:
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(values, updated_at=self._now())
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def _run(self, path: Path, payload: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            self._update(path, status="RUNNING", progress=5)
            profile = None if payload.get("event_id") == "E001" else tuple(payload["profile_mm"])
            scenario = SwmmScenario(scenario_id=payload["scenario_id"], rainfall_profile_mm=profile)
            physics_job = self.physics.submit(scenario)
            while physics_job["status"] in {"queued", "running"}:
                time.sleep(0.25)
                physics_job = self.physics.status(physics_job["simulation_id"])
                self._update(path, status="RUNNING", progress=25 if physics_job["status"] == "running" else 10,
                             physics_simulation_id=physics_job["simulation_id"])
            if physics_job["status"] != "completed":
                self._update(path, status="FAILED_PHYSICS", error=physics_job.get("error", "SWMM failed"), progress=100)
                return
            self._update(path, status="PHYSICS_COMPLETE", progress=55, physics_simulation_id=physics_job["simulation_id"],
                         physics_cache_hit=physics_job.get("cache_hit", False), physics_summary=physics_job.get("summary"))
            self._update(path, status="ML_RUNNING", progress=65)
            prediction = self._predict(payload, physics_job["simulation_id"])
            physics_manifest = self.physics.runs / physics_job["scenario_hash"] / "manifest.json"
            execution = json.loads(physics_manifest.read_text(encoding="utf-8")).get("execution", {}) if physics_manifest.is_file() else {}
            result_path = self.results_dir / f"{path.stem}_risk_map.json"
            result_path.write_text(json.dumps(prediction, indent=2), encoding="utf-8")
            self._update(path, status="COMPLETE", progress=100, result_path=str(result_path),
                         prediction_count=len(prediction["risk_map"]), physics_supported_cells=prediction["physics_supported_cells"],
                         elapsed_seconds=round(time.perf_counter() - started, 3), risk_summary=prediction["summary"],
                         physics_supported=prediction["physics_supported_cells"] > 0,
                         prediction_mode="MIXED_PHYSICS_AND_GIS_FALLBACK",
                         performance={**prediction["performance"], "swmm_runtime_seconds": execution.get("runtime_seconds"),
                                      "swmm_cache_hit": physics_job.get("cache_hit", False),
                                      "end_to_end_seconds": round(time.perf_counter() - started, 3)})
        except Exception as exc:
            LOGGER.exception("Scenario job %s failed", path.stem)
            self._update(path, status="FAILED_ML", error=f"{type(exc).__name__}: {exc}", progress=100,
                         elapsed_seconds=round(time.perf_counter() - started, 3))

    def _predict(self, payload: dict[str, Any], physics_id: str) -> dict[str, Any]:
        ds = self.ml.dataset
        md = self.ml.physics_metadata
        gis_md = self.ml.citywide_metadata
        base = ds.drop_duplicates("grid_id").set_index("grid_id")
        grid_csv = self.physics.results(physics_id, "grid_event_metrics.csv")
        mapping = pd.read_csv(grid_csv)
        # Detailed result tables preserve the provenance of each hydraulic quantity.
        base_path = self.physics.results(physics_id, "grid_physics_timeseries.csv")
        timeseries = pd.read_csv(base_path)
        grouped = timeseries.groupby("grid_id", sort=False)
        physics_by_grid = grouped.agg(
            swmm_nearest_node_depth_proxy_m=("nearest_node_depth_m", "max"),
            swmm_node_flooding_m3=("nearest_node_flooding_m3", "sum"),
            swmm_peak_conduit_flow_m3s=("nearest_conduit_flow_m3s", lambda values: float(values.abs().max())),
            swmm_peak_conduit_velocity_m_s=("nearest_conduit_velocity_ms", lambda values: float(values.abs().max())),
            swmm_subcatchment_runoff_mm=("surface_runoff_mm", "sum"), swmm_surface_runoff_mm=("surface_runoff_mm", "sum"))
        profile = [float(value) for value in payload["profile_mm"]]
        def peak_window(intervals: int) -> float:
            return max((sum(profile[i:i + intervals]) for i in range(max(1, len(profile) - intervals + 1))), default=sum(profile))
        base["rainfall_total_mm"] = float(payload["rainfall_total_mm"])
        base["rainfall_24h_mm"] = peak_window(96)
        base["rainfall_12h_mm"] = peak_window(48)
        base["rainfall_6h_mm"] = peak_window(24)
        base["rainfall_3h_mm"] = peak_window(12)
        base["rainfall_1h_mm"] = peak_window(4)
        base["peak_15min_mm"] = max(payload["profile_mm"])
        base["peak_1h_mm"] = max(sum(payload["profile_mm"][i:i + 4]) for i in range(max(1, len(payload["profile_mm"]) - 3)))
        base["rainfall_total_mm"] = float(payload["rainfall_total_mm"])
        for col in physics_by_grid.columns:
            base[col] = physics_by_grid[col].reindex(base.index)
        supported_mask = base.physics_coverage.astype(bool) & base.swmm_nearest_node_depth_proxy_m.notna()
        xgb = XGBClassifier()
        xgb.load_model(self.ml.artifacts / "models" / "terra05_xgb_v1.json")
        gis = XGBClassifier()
        gis.load_model(self.ml.artifacts / "models" / "terra05_xgb_citywide_gis.json")
        scores = pd.Series(index=base.index, dtype=float)
        ml_started = time.perf_counter()
        if supported_mask.any():
            features = md["features"]
            x = base.loc[supported_mask, features].replace([np.inf, -np.inf], np.nan)
            scores.loc[supported_mask] = xgb.predict_proba(x)[:, 1]
        fallback_mask = ~supported_mask
        gis_features = gis_md["features"]
        xg = base.loc[fallback_mask, gis_features].replace([np.inf, -np.inf], np.nan)
        scores.loc[fallback_mask] = gis.predict_proba(xg)[:, 1]
        thresholds = float(md.get("selected_threshold", 0.5))
        rows = []
        for grid_id, score in scores.items():
            row = base.loc[grid_id]
            rows.append({"grid_id": int(grid_id), "ward": str(row.ward), "risk_score": float(score),
                         "risk_level": self.ml._risk_level(float(score), md if bool(row.physics_coverage) else gis_md),
                         "physics_supported": bool(row.physics_coverage),
                         "prediction_mode": "PHYSICS_INFORMED_EXTRAPOLATION" if bool(row.physics_coverage) else "GIS_ONLY_FALLBACK",
                         "predicted_label": int(score >= thresholds) if bool(row.physics_coverage) else None,
                         "hydraulic_depth_proxy_m": float(row.swmm_nearest_node_depth_proxy_m) if pd.notna(row.swmm_nearest_node_depth_proxy_m) else None})
        ml_elapsed = time.perf_counter() - ml_started
        rows.sort(key=lambda item: item["risk_score"], reverse=True)
        asset_rows = [item for item in rows if bool(base.loc[item["grid_id"], "has_hospital"]) or bool(base.loc[item["grid_id"], "is_critical_asset_cell"])]
        total = len(rows)
        return {"scenario_id": payload["scenario_id"], "event_id": payload["event_id"], "rainfall_source": payload["rainfall_source"],
                "rainfall_hash": payload["rainfall_hash"], "rainfall_total_mm": payload["rainfall_total_mm"],
                "prediction_semantics": "Uncalibrated scores extrapolated from E001 supplied labels; not calibrated event probabilities or observed flood depths",
                "target_provenance": "supplied historical flood grid lacks independently verified July-2005 event match",
                "risk_map": rows, "critical_assets": asset_rows[:100], "physics_supported_cells": int(supported_mask.sum()),
                "prediction_mode_counts": {"physics_informed_extrapolation": int(supported_mask.sum()), "gis_only_fallback": int(fallback_mask.sum())},
                "summary": {"grid_cells": total, "peak_risk_score": rows[0]["risk_score"] if rows else None,
                            "high_or_very_high_cells": sum(r["risk_level"] in {"HIGH", "VERY_HIGH"} for r in rows),
                            "critical_asset_cells": len(asset_rows)},
                "decision_support": ["Prioritize field review of the highest ranked risk cells and exposed critical-asset cells.",
                                     "Scores are uncalibrated scenario rankings; confirm against current observations before operational action."],
                "performance": {"physics_cache": "reused or computed by SWMM job", "ml_inference_seconds": round(ml_elapsed, 6),
                                "prediction_cells": len(rows)}}

    def status(self, simulation_id: str) -> dict[str, Any]:
        path = self._path(simulation_id)
        if not path.is_file():
            raise LookupError(f"Unknown scenario simulation id: {simulation_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def results(self, simulation_id: str) -> dict[str, Any]:
        record = self.status(simulation_id)
        if record["status"] != "COMPLETE":
            raise RuntimeError(f"Scenario is {record['status']}")
        return json.loads(Path(record["result_path"]).read_text(encoding="utf-8"))
