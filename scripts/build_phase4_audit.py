"""Build provenance-first Phase 4 event registry and integrity artifacts."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ml_phase4"


def main() -> None:
    datasets, reports = OUT / "datasets", OUT / "reports"
    datasets.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(ROOT / "data/processed/mumbai_flood_events_v1.csv")
    rain = pd.read_csv(ROOT / "data/processed/rainfall_observations_v1.csv")
    target = pd.read_csv(ROOT / "data/processed/flood_grid_100m.csv")
    target_source = "data/processed/flood_grid_100m.csv; supplied BMC flooding-spot-derived grid; no event date join"
    rows = []
    for event in events.itertuples(index=False):
        obs = rain[rain.event_id.eq(event.event_id)]
        verified_values = obs[obs.source_quality.astype(str).str.startswith("verified")]
        exact_event_target = False  # Current target has no event_id or observation date field.
        if event.event_id == "E001":
            eligibility, role, completeness = "INSUFFICIENT_PROVENANCE", "RAIN_ONLY_FOR_SUPERVISED_PHASE4", "nine verified 3-hour intervals; 15-minute profile is reconstructed"
            rainfall_source = "IMD MAUSAM Table 7; Santacruz; verified cumulative and interval data"
            swmm = "SUITABLE_FOR_REPLAY; baseline 2005 run already exists"
        elif event.event_id == "E002":
            eligibility, role, completeness = "RAIN_ONLY", "PHYSICS_ONLY_NOT_TRAINING", "partial bulletin values: 106 mm/24h plus 63 mm/3h; timing overlap/window requires resolution"
            rainfall_source = "IMD special bulletin; partial accumulation windows"
            swmm = "NOT_RUN; insufficiently defined temporal profile"
        elif event.event_id in {"E003", "E004"}:
            eligibility, role, completeness = "INSUFFICIENT_RAINFALL", "PHYSICS_ONLY_NOT_TRAINING", "event named but station/date rainfall values pending"
            rainfall_source, swmm = "IMD citation only; no observations in repository", "NOT_RUN; no quantitative hyetograph"
        else:
            eligibility, role, completeness = "INSUFFICIENT_PROVENANCE", "CANDIDATE_ONLY", "specific rainfall period and flood match not verified"
            rainfall_source, swmm = "candidate IMD event only", "NOT_RUN"
        rows.append({"event_id": event.event_id, "date_or_window": f"{event.event_start or ''} — {event.event_end or ''}",
                     "duration": completeness, "rainfall_source": rainfall_source,
                     "temporal_resolution": "; ".join(sorted(set(obs.accumulation_period_hours.dropna().astype(int).astype(str)))) + " hour aggregates" if not obs.empty else "unavailable",
                     "rainfall_completeness": completeness, "spatial_coverage": "Santacruz station; no gridded rainfall field",
                     "flood_observation_availability": "supplied flood grid exists but not event matched",
                     "flood_observation_date": "unknown in target source", "flood_observation_source": target_source,
                     "target_availability": "supplied label available; excluded from Phase 4 event-supervised use",
                     "target_quality": "event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target",
                     "swmm_suitability": swmm, "provenance": "rainfall-source=" + str(event.rainfall_source) + "; target provenance unresolved",
                     "event_eligibility": eligibility, "event_role": role, "verified_rainfall_record_count": len(verified_values),
                     "event_matched_target": exact_event_target})
    registry = pd.DataFrame(rows)
    registry.to_csv(datasets / "event_registry.csv", index=False)
    # Preserve E001 as an explicitly non-eligible supplied-label candidate, not as a multi-event training row.
    phase3 = pd.read_csv(ROOT / "data/ml_phase3/datasets/training_master.csv", low_memory=False)
    candidate = phase3.copy()
    candidate["event_id"] = "E001"
    candidate["scenario_id"] = "historical_2005_candidate_label"
    candidate["target_type"] = "supplied_historical_waterlogging_label"
    candidate["event_target_eligibility"] = "INSUFFICIENT_PROVENANCE"
    candidate["event_target_match_verified"] = False
    candidate.to_csv(datasets / "multi_event_master.csv", index=False)
    for name in ("train", "validation", "test"):
        candidate.iloc[0:0].to_csv(datasets / f"{name}.csv", index=False)
    duplicates = int(candidate.duplicated(["event_id", "grid_id"]).sum())
    conflicting = int(candidate.groupby(["event_id", "grid_id"]).flood_label.nunique().gt(1).sum())
    unique_keys = candidate[["event_id", "grid_id"]].drop_duplicates().shape[0]
    digest = hashlib.sha256((datasets / "multi_event_master.csv").read_bytes()).hexdigest()
    counts = registry.event_eligibility.value_counts().to_dict()
    (reports / "dataset_integrity.md").write_text(
        "# Phase 4 Dataset Integrity\n\n"
        f"- Candidate E001 event-grid rows retained for audit only: {len(candidate):,}; unique event/grid keys: {unique_keys:,}.\n"
        f"- Duplicate event/grid keys: {duplicates}; conflicting labels per key: {conflicting}.\n"
        f"- Event-eligible supervised rows: 0; train/validation/test files are empty by design.\n"
        f"- Supplied target positives: {int(target.flood_label.sum()):,} of {len(target):,}; label source does not establish a July 2005 match.\n"
        f"- Registry eligibility counts: {counts}.\n- Canonical candidate dataset SHA-256: `{digest}`.\n\n"
        "No SWMM output is used as a target. E001 labels remain unverified for this rainfall event; other events have no defensible matching spatial labels. Scenario outputs are for simulation and exploratory ranking, not supervised validation.\n",
        encoding="utf-8")
    (reports / "event_registry.md").write_text(
        "# Phase 4 Historical Event Registry\n\n"
        "| Event | Rainfall evidence | Spatial target match | Eligibility | SWMM status |\n|---|---|---|---|---|\n" +
        "\n".join(f"| {r.event_id} | {r.rainfall_completeness} | {r.target_quality} | {r.event_eligibility} | {r.swmm_suitability} |" for r in registry.itertuples()) +
        "\n\nThe flood target source documents BMC flooding spots from 2019–2023; the supplied grid itself has no event/date field and cannot be independently matched to E001. Target type therefore remains `supplied_historical_waterlogging_label`. No events qualify for Phase 4 event-held-out supervised training or evaluation. Historical E001 replay remains available with reconstructed 15-minute rainfall explicitly identified. E002 is partial rainfall-only; E003/E004 lack verified rainfall amounts; E005 remains a candidate. No external live rainfall provider is configured.\n",
        encoding="utf-8")
    (reports / "multi_event_validation.md").write_text(
        "# Multi-event validation\n\nMULTI_EVENT_SUPERVISED_VALIDATION_NOT_SUPPORTED\n\n"
        "No event has both defensible rainfall provenance and an independently event-matched spatial flood target. The Phase 3 model and metrics are retained as the existing single-event spatial-block baseline only; they are not presented as unseen-event validation. Phase 4 scenario scores apply that model to new rainfall/SWMM features and are explicitly marked exploratory extrapolations.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
