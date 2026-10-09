"""Phase 3 XGBoost prediction service; SWMM is never run in this request path."""
from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any


class Phase3MLService:
    def __init__(self, root: Path):
        self.root = root
        self.artifacts = root / "data" / "ml_phase3"

    @cached_property
    def dataset(self):
        import pandas as pd
        return pd.read_csv(self.artifacts / "datasets" / "training_master.csv", low_memory=False)

    @cached_property
    def physics_metadata(self) -> dict[str, Any]:
        return json.loads((self.artifacts / "models" / "terra05_xgb_metadata.json").read_text(encoding="utf-8"))

    @cached_property
    def citywide_metadata(self) -> dict[str, Any]:
        return json.loads((self.artifacts / "models" / "terra05_xgb_citywide_gis_metadata.json").read_text(encoding="utf-8"))

    @cached_property
    def physics_model(self):
        from xgboost import XGBClassifier
        model = XGBClassifier()
        model.load_model(self.artifacts / "models" / "terra05_xgb_v1.json")
        return model

    @cached_property
    def citywide_model(self):
        from xgboost import XGBClassifier
        model = XGBClassifier()
        model.load_model(self.artifacts / "models" / "terra05_xgb_citywide_gis.json")
        return model

    @staticmethod
    def _risk_level(score: float, metadata: dict[str, Any]) -> str:
        cuts = metadata.get("risk_level_cutpoints_validation_quantiles", {})
        q50, q75, q90 = (float(cuts.get(str(q), 1.0)) for q in (0.5, 0.75, 0.9))
        if score >= q90:
            return "VERY_HIGH"
        if score >= q75:
            return "HIGH"
        if score >= q50:
            return "MODERATE"
        return "LOW"

    def predict(self, grid_id: int, scenario_id: str = "historical_2005") -> dict[str, Any]:
        import pandas as pd

        if scenario_id != "historical_2005":
            raise ValueError("Phase 3 models currently support only the historical_2005 feature event; other rainfall scenarios lack matching training labels/physics features")
        match = self.dataset[self.dataset.grid_id.eq(grid_id)]
        if match.empty:
            raise LookupError(f"Unknown grid_id {grid_id}")
        row = match.iloc[0]
        supported = bool(row.physics_coverage)
        metadata = self.physics_metadata if supported else self.citywide_metadata
        model = self.physics_model if supported else self.citywide_model
        features = metadata["features"]
        X = pd.DataFrame([{name: row.get(name) for name in features}], columns=features)
        score = float(model.predict_proba(X)[0, 1])
        return {
            "grid_id": int(grid_id), "ward": str(row.ward), "scenario_id": scenario_id,
            "model_version": metadata["model_version"],
            "prediction_mode": "physics_supported" if supported else "citywide_gis_only",
            "physics_supported": supported, "risk_score": score,
            "risk_score_semantics": "Uncalibrated model ranking score; not a calibrated event probability",
            "risk_level": self._risk_level(score, metadata),
            "predicted_label": int(score >= float(metadata.get("selected_threshold", metadata.get("threshold", 0.5)))) if supported else None,
            "target_definition": "Historical July-2005 flood_label per Phase 3 target definition; source event provenance needs confirmation",
            "limitations": [
                "The 15-minute July 2005 rainfall profile is reconstructed from three-hour IMD observations.",
                "SWMM is executable but not calibrated or hydraulically validated against event-matched observed depths/flows.",
                "Nearest-node depth is a hydraulic proxy, not street flood depth.",
                "Citywide uncovered cells use GIS-only model features and have no SWMM physics support.",
            ],
        }
