"""Freeze Phase 4 model metadata, comparisons and reproducibility reports."""
from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "data/ml_phase3"
OUT = ROOT / "data/ml_phase4"


def main() -> None:
    models, reports, scenarios = OUT / "models", OUT / "reports", OUT / "scenarios"
    models.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    scenarios.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PHASE3 / "models/feature_schema.json", models / "feature_schema.json")
    phase3_md = json.loads((PHASE3 / "models/terra05_xgb_metadata.json").read_text(encoding="utf-8"))
    gis_md = json.loads((PHASE3 / "models/terra05_xgb_citywide_gis_metadata.json").read_text(encoding="utf-8"))
    metadata = {
        "model_version": "terra05-ml-v2.0.0",
        "model_status": "NOT_TRAINED_NO_EVENT_MATCHED_SUPERVISED_TARGETS",
        "production_model": "terra05-xgb-v1.0.0 (Phase 3 baseline retained)",
        "training_events": [], "validation_events": [], "test_events": [],
        "target_type": "supplied_historical_waterlogging_label",
        "target_provenance": "Supplied flood-grid source does not independently match target cells to event E001",
        "feature_groups": {"GIS": 25, "rainfall": 8, "SWMM_nonempty": 6},
        "swmm_model_version": phase3_md["swmm_model_version"],
        "physics_coverage_cells": 1516, "citywide_grid_cells": 47758,
        "training_dataset_sha256": None,
        "validation_strategy": "No Phase 4 event holdout possible; retain Phase 3 spatial-block metrics as single-event label agreement only",
        "threshold": phase3_md["selected_threshold"], "random_seed": 42,
        "existing_phase3_model_metadata": "../ml_phase3/models/terra05_xgb_metadata.json",
        "validation_status": "MULTI_EVENT_SUPERVISED_VALIDATION_NOT_SUPPORTED",
        "note": "No terra05_ml_v2.json estimator is emitted because fitting without eligible event-matched targets would fabricate supervised evidence.",
    }
    (models / "terra05_ml_v2_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (models / "thresholds.json").write_text(json.dumps({"production_baseline": phase3_md["selected_threshold"],
        "threshold_source": "Phase 3 validation-selected threshold; not an official operational warning threshold",
        "citywide_gis_threshold": gis_md.get("threshold"), "phase4_threshold_selected": False}, indent=2), encoding="utf-8")
    comparisons = pd.read_csv(PHASE3 / "reports/experiment_comparison.csv")
    comparisons.insert(0, "evaluation_scope", "Phase 3 E001 supplied-label spatial-block test; not event holdout")
    comparisons.to_csv(reports / "model_comparison.csv", index=False)
    shutil.copyfile(PHASE3 / "reports/feature_importance.csv", reports / "feature_importance.csv")

    demo_path = scenarios / "custom_demo_150mm_6h_run.json"
    demo = json.loads(demo_path.read_text(encoding="utf-8")) if demo_path.is_file() else {}
    job = demo.get("job", {})
    perf = job.get("performance", {})
    physics_id = job.get("physics_simulation_id")
    physics_job_path = ROOT / "data/swmm_phase2/manifests/jobs" / f"{physics_id}.json" if physics_id else None
    physics_job = json.loads(physics_job_path.read_text(encoding="utf-8")) if physics_job_path and physics_job_path.is_file() else {}
    physics_manifest_path = ROOT / "data/swmm_phase2/runs" / physics_job.get("scenario_hash", "") / "manifest.json"
    physics_manifest = json.loads(physics_manifest_path.read_text(encoding="utf-8")) if physics_manifest_path.is_file() else {}
    if physics_manifest_path.is_file():
        input_path = Path(physics_manifest.get("input_path", ""))
        physics_manifest.update({"event_id": None, "scenario_id": job.get("scenario_id"), "model_version": "terra05-swmm-v1.0.0",
            "input_hash": hashlib.sha256(input_path.read_bytes()).hexdigest() if input_path.is_file() else physics_manifest.get("model_sha256"),
            "rainfall_hash": job.get("rainfall_hash"), "run_timestamp": physics_manifest.get("completed_at", job.get("updated_at"))})
        physics_manifest_path.write_text(json.dumps(physics_manifest, indent=2), encoding="utf-8")
    execution = physics_manifest.get("execution", {})
    result = demo.get("result", {})
    scenario_row = [{"scenario_id": job.get("scenario_id"), "simulation_id": job.get("simulation_id"), "mode": job.get("mode"),
        "label": demo.get("scenario_label"), "rainfall_source": job.get("rainfall_source"), "rainfall_total_mm": job.get("rainfall_total_mm"),
        "duration_minutes": job.get("duration_minutes"), "rainfall_hash": job.get("rainfall_hash"), "status": job.get("status"),
        "swmm_simulation_id": physics_id, "swmm_solver_runtime_seconds": execution.get("runtime_seconds"),
        "swmm_cache_hit_on_final_job": perf.get("swmm_cache_hit"), "ml_inference_seconds": result.get("performance", {}).get("ml_inference_seconds"),
        "end_to_end_seconds": demo.get("end_to_end_elapsed_seconds"), "physics_supported_cells": job.get("physics_supported_cells"),
        "prediction_cells": result.get("risk_summary", {}).get("grid_cells"), "high_or_very_high_cells": result.get("risk_summary", {}).get("high_or_very_high_cells"),
        "critical_asset_cells": result.get("risk_summary", {}).get("critical_asset_cells") }]
    replay_path = scenarios / "historical_replay_E001_run.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8")) if replay_path.is_file() else {}
    rjob = replay.get("job", {})
    rperf = rjob.get("performance", {})
    rresult = replay.get("result", {})
    if rjob.get("physics_simulation_id"):
        replay_job_file = ROOT / "data/swmm_phase2/manifests/jobs" / f"{rjob['physics_simulation_id']}.json"
        if replay_job_file.is_file():
            replay_physics_job = json.loads(replay_job_file.read_text(encoding="utf-8"))
            replay_manifest_path = ROOT / "data/swmm_phase2/runs" / replay_physics_job.get("scenario_hash", "") / "manifest.json"
            if replay_manifest_path.is_file():
                replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
                replay_input = Path(replay_manifest.get("input_path", ""))
                replay_manifest.update({"event_id": "E001", "scenario_id": "historical_2005", "model_version": "terra05-swmm-v1.0.0",
                    "input_hash": hashlib.sha256(replay_input.read_bytes()).hexdigest() if replay_input.is_file() else replay_manifest.get("model_sha256"),
                    "rainfall_hash": rjob.get("rainfall_hash"), "run_timestamp": replay_manifest.get("completed_at", rjob.get("updated_at"))})
                replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2), encoding="utf-8")
    scenario_row.append({"scenario_id": rjob.get("scenario_id"), "simulation_id": rjob.get("simulation_id"), "mode": rjob.get("mode"),
        "label": replay.get("scenario_label"), "rainfall_source": rjob.get("rainfall_source"), "rainfall_total_mm": rjob.get("rainfall_total_mm"),
        "duration_minutes": rjob.get("duration_minutes"), "rainfall_hash": rjob.get("rainfall_hash"), "status": rjob.get("status"),
        "swmm_simulation_id": rjob.get("physics_simulation_id"), "swmm_solver_runtime_seconds": rperf.get("swmm_runtime_seconds"),
        "swmm_cache_hit_on_final_job": rperf.get("swmm_cache_hit"), "ml_inference_seconds": rresult.get("performance", {}).get("ml_inference_seconds"),
        "end_to_end_seconds": rperf.get("end_to_end_seconds"), "physics_supported_cells": rjob.get("physics_supported_cells"),
        "prediction_cells": rresult.get("summary", {}).get("grid_cells"),
        "high_or_very_high_cells": rresult.get("summary", {}).get("high_or_very_high_cells"),
        "critical_asset_cells": rresult.get("summary", {}).get("critical_asset_cells")})
    pd.DataFrame(scenario_row).to_csv(scenarios / "scenario_registry.csv", index=False)
    (OUT / "physics/manifests").mkdir(parents=True, exist_ok=True)
    (OUT / "physics/event_runs").mkdir(parents=True, exist_ok=True)
    (OUT / "physics/hydraulic_features").mkdir(parents=True, exist_ok=True)
    (OUT / "physics/manifests/E001_historical_replay.json").write_text(json.dumps({
        "event_id": "E001", "scenario_id": "historical_2005", "model_version": "terra05-swmm-v1.0.0",
        "run_timestamp": rjob.get("updated_at"), "rainfall_hash": rjob.get("rainfall_hash"),
        "simulation_id": rjob.get("physics_simulation_id"), "cache_hit": rperf.get("swmm_cache_hit"),
        "validation_status": rjob.get("validation_status"), "results_source": "data/swmm_phase2 Phase 1 baseline reuse",
        "target_usage": "not a Phase 4 supervised target; label event match unresolved"}, indent=2), encoding="utf-8")
    (OUT / "physics/manifests/custom_demo_150mm_6h.json").write_text(json.dumps({
        "event_id": None, "scenario_id": job.get("scenario_id"), "model_version": "terra05-swmm-v1.0.0",
        "run_timestamp": job.get("updated_at"), "rainfall_hash": job.get("rainfall_hash"),
        "simulation_id": physics_id, "input_hash": physics_manifest.get("input_hash"),
        "scenario_hash": physics_job.get("scenario_hash"), "execution": execution,
        "result_dir": physics_manifest.get("result_dir"), "validation_status": job.get("validation_status"),
        "scenario_label": demo.get("scenario_label")}, indent=2), encoding="utf-8")
    (OUT / "manifests").mkdir(parents=True, exist_ok=True)
    (OUT / "manifests/phase4_manifest.json").write_text(json.dumps({
        "phase": "TERRA05 Phase 4", "status": "COMPLETE_WITH_DATA_LIMITATIONS",
        "event_registry": "datasets/event_registry.csv", "multi_event_supervised_validation": "NOT_SUPPORTED",
        "candidate_dataset_rows": 47758, "eligible_train_rows": 0, "custom_swmm_solver_runs": 1,
        "historical_replay_solver_runs": 0, "demo_scenario": job.get("scenario_id"),
        "demo_risk_result": "predictions/scenario_predictions/" + str(job.get("simulation_id")) + "_risk_map.json",
        "model_v2_status": "not fit: no event-matched supervised targets"}, indent=2), encoding="utf-8")

    lines = [
        "# TERRA05 Phase 4 Final Report", "",
        "## 1. Objective", "Extend the existing Phase 3 pipeline with provenance-audited event handling and asynchronous SWMM-to-ML scenario execution.", "",
        "## 2. Existing Phase 3 Baseline", "Retained `terra05-xgb-v1.0.0`, its Phase 3 spatial-block evaluation and the Random Forest benchmark. These are E001 supplied-label spatial tests, not event-holdout validation.", "",
        "## 3. Historical Event Registry", "Five events E001–E005 are recorded in `event_registry.csv`.", "",
        "## 4. Event Eligibility", "E001: insufficient target provenance; E002: rain-only partial bulletin; E003/E004: insufficient rainfall amounts; E005: insufficient provenance/candidate. No Phase 4 supervised-eligible event.", "",
        "## 5. Multi-Event Dataset", "47,758 event-grid candidate rows retained from E001 with `event_target_eligibility=INSUFFICIENT_PROVENANCE`; zero rows admitted to train/validation/test. 47,758 unique event/grid keys; 0 duplicates and 0 conflicts.", "",
        "## 6. SWMM Event Simulations", f"One new deterministic synthetic custom hyetograph was executed through existing EPA SWMM Dynamic Wave; runtime {execution.get('runtime_seconds')} s. Historical E001 is replayable through the preserved Phase 1 result cache. No additional historical events were simulated because available rainfall inputs are incomplete or ambiguous.", "",
        "## 7. Physics Feature Generation", "Existing spatial mapping and extraction reused. The demonstration produced 1,516 physics-supported Ward L cells; nearest-node depth remains `HYDRAULIC_PROXY`. No surface depth is returned.", "",
        "## 8. ML Training", "No Phase 4 model was fitted because no event-matched target is defensible. The Phase 3 model is reused only as an explicitly marked exploratory scenario-ranking baseline.", "",
        "## 9. Spatial Validation", "Existing Phase 3 2 km spatial-block validation remains unchanged and applies to one supplied-label dataset only.", "",
        "## 10. Unseen Event Validation", "MULTI_EVENT_SUPERVISED_VALIDATION_NOT_SUPPORTED. No defensible event-level generalization metric can be reported.", "",
        "## 11. GIS Baseline", "Phase 3 spatial test PR-AUC 0.1853, ROC-AUC 0.5670, precision 0.1478, recall 0.9677, F1 0.2564.", "",
        "## 12. GIS + Rainfall", "Phase 3 spatial test PR-AUC 0.1926, ROC-AUC 0.5807, precision 0.1526, recall 0.9355, F1 0.2624.", "",
        "## 13. GIS + Rainfall + SWMM", "Phase 3 spatial test PR-AUC 0.2408, ROC-AUC 0.6204, precision 0.1445, recall 0.9839, F1 0.2521. These are not multi-event results.", "",
        "## 14. Random Forest", "Phase 3 same-split benchmark test PR-AUC 0.2489, ROC-AUC 0.6489, precision 0.1706, recall 0.9355, F1 0.2886.", "",
        "## 15. Physics Contribution", "On the Phase 3 test split, SWMM features add +0.0482 absolute PR-AUC vs GIS + rainfall. This is single-event supplied-label association, not evidence of unseen-event benefit.", "",
        "## 16. Final Model Selection", "No Phase 4 model selected. Phase 3 Random Forest has higher test PR-AUC/ROC-AUC than the XGBoost physics model, but data provenance prevents declaring an event-generalizing production winner. Existing API baseline remains in place.", "",
        "## 17. Real-Time Scenario Engine", "Manual total/duration, normalized 15-minute profiles and E001 historical replay supported. Jobs are asynchronous and cache-keyed. External live/forecast sources are not configured; UI states this.", "",
        "## 18. API Architecture", "`POST /api/v1/scenario/run`; `GET /api/v1/scenario/{id}`; `GET /api/v1/scenario/{id}/results`. Existing ML and SWMM APIs remain.", "",
        "## 19. Frontend Integration", "Added a scenario panel with historical replay/custom rainfall, job polling, cache/status, risk summary, top-ranked cells and provenance caveats. A separate Scenario ML Risk fill/outline layer updates for the mapped Ward L grid cells; the existing risk grid and fast 2D engine remain separate.", "",
        "## 20. Critical Infrastructure", "Scenario result ranks cells with existing hospital/critical-asset flags and surfaces top exposed asset cells. This is grid-level exposure, not asset-specific impact measurements.", "",
        "## 21. Decision Support", "Outputs field-review priorities for high-risk and critical-asset grid cells and explicitly states scores are uncalibrated and need current observation confirmation.", "",
        "## 22. Performance", f"Demo job end-to-end (cached SWMM): {demo.get('end_to_end_elapsed_seconds')} s; ML inference: {result.get('performance', {}).get('ml_inference_seconds')} s for {result.get('risk_summary', {}).get('grid_cells')} citywide cells; cold SWMM solver runtime: {execution.get('runtime_seconds')} s; final SWMM cache hit: {perf.get('swmm_cache_hit')}. Timings are measured on this machine.", "",
        "## 23. Limitations", "No valid event-matched labels for event holdout; target source date unresolved; reconstructed rainfall; SWMM uncalibrated; surface coupling absent; only Ward L hydraulic coverage; scenario scores are out-of-domain extrapolations; no live rainfall provider.", "",
        "## 24. Reproducibility", "Run `python scripts/build_phase4_audit.py`, `python scripts/run_phase4_demo.py`, and `python scripts/build_phase4_reports.py`. Model comparison source and hashes are preserved under `data/ml_phase3` and `data/ml_phase4`.", "",
        "## 25. Final Verdict", "PHASE_4_COMPLETE_WITH_DATA_LIMITATIONS for the implemented/audited scenario workflow and exercised demo. Multi-event supervised training and unseen-event validation remain unsupported by the repository's labels; no scientific generalization claim is made.", "",
    ]
    (reports / "phase4_final_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
