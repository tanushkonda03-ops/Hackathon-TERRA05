from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    root: Path
    model_path: Path
    ml_features_path: Path
    risk_grid_path: Path
    rainfall_catalog_path: Path
    rainfall_metadata_path: Path
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        root = Path(os.getenv("TERRA05_ROOT", Path(__file__).resolve().parents[1])).resolve()
        origins = tuple(
            origin.strip()
            for origin in os.getenv("TERRA05_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000").split(",")
            if origin.strip()
        )
        return cls(
            root=root,
            model_path=Path(os.getenv("TERRA05_MODEL_PATH", root / "outputs/models/ward_flood_susceptibility_rf_tuned.joblib")),
            ml_features_path=Path(os.getenv("TERRA05_FEATURES_PATH", root / "data/ml_ready/ml_master_spatial_features.csv")),
            risk_grid_path=Path(os.getenv("TERRA05_RISK_GRID_PATH", root / "data/processed/flood_grid_100m.geojson")),
            rainfall_catalog_path=Path(os.getenv("TERRA05_RAINFALL_CATALOG", root / "data/swmm_ready/swmm_rainfall_catalog.csv")),
            rainfall_metadata_path=Path(os.getenv("TERRA05_RAINFALL_METADATA", root / "data/swmm_ready/swmm_rainfall_metadata.json")),
            cors_origins=origins,
        )
