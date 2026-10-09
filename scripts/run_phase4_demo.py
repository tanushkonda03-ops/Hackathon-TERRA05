"""Run the repeatable synthetic 150 mm / 6 h SWMM-to-ML demonstration."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import app


def main() -> None:
    started = time.perf_counter()
    with TestClient(app) as client:
        profile = [0.0] * 8 + [5.0] * 8 + [13.75] * 8
        response = client.post("/api/v1/scenario/run", json={"mode": "custom", "profile_mm": profile})
        response.raise_for_status()
        job = response.json()
        while job["status"] not in {"COMPLETE", "FAILED_PHYSICS", "FAILED_ML", "FAILED_INPUT"}:
            time.sleep(1)
            job = client.get(f"/api/v1/scenario/{job['simulation_id']}").json()
        run = {"job": job, "end_to_end_elapsed_seconds": round(time.perf_counter() - started, 3),
               "scenario_label": "Synthetic user-defined scenario; not an observed event",
               "temporal_profile_mm_per_15min": profile}
        if job["status"] == "COMPLETE":
            result = client.get(f"/api/v1/scenario/{job['simulation_id']}/results").json()
            run["result"] = {"scenario_id": result["scenario_id"], "risk_summary": result["summary"],
                             "physics_supported_cells": result["physics_supported_cells"],
                             "prediction_mode_counts": result["prediction_mode_counts"],
                             "top_risk_cells": result["risk_map"][:10],
                             "critical_assets": result["critical_assets"][:10],
                             "decision_support": result["decision_support"], "performance": result["performance"]}
        out = ROOT / "data/ml_phase4/scenarios/custom_demo_150mm_6h_run.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(run, indent=2), encoding="utf-8")
        print(json.dumps(run, indent=2))
        if job["status"] != "COMPLETE":
            raise SystemExit(f"Phase 4 demo did not complete: {job.get('error')}")


if __name__ == "__main__":
    main()
