"""Exercise the historical E001 SWMM/ML replay contract and save its record."""
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
    with TestClient(app) as client:
        response = client.post("/api/v1/scenario/run", json={"mode": "historical_replay", "event_id": "E001"})
        response.raise_for_status()
        job = response.json()
        while job["status"] not in {"COMPLETE", "FAILED_PHYSICS", "FAILED_ML", "FAILED_INPUT"}:
            time.sleep(0.5)
            job = client.get(f"/api/v1/scenario/{job['simulation_id']}").json()
        record = {"job": job, "scenario_label": "Historical E001 replay; 15-minute hyetograph reconstructed from observed 3-hour totals"}
        if job["status"] == "COMPLETE":
            record["result"] = client.get(f"/api/v1/scenario/{job['simulation_id']}/results").json()
        (ROOT / "data/ml_phase4/scenarios/historical_replay_E001_run.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps({"status": job["status"], "simulation_id": job["simulation_id"],
                          "cache_hit": job.get("cache_hit"), "error": job.get("error")}, indent=2))
        if job["status"] != "COMPLETE":
            raise SystemExit(f"Historical replay failed: {job.get('error')}")


if __name__ == "__main__":
    main()
