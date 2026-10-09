"""Generate and validate TERRA05 rainfall scenarios without network side effects.

All rainfall values in the catalogue and ``.dat`` files are 15-minute depths
in millimetres. Intensities are derived interval-average values in mm/hour.
The 2005 series is a synthetic temporal disaggregation of 3-hour source totals,
not directly observed 15-minute rainfall.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

INTERVAL_MINUTES = 15
INTERVAL_HOURS = 0.25
PROFILE = (0.03, 0.05, 0.08, 0.12, 0.18, 0.24, 0.14, 0.07, 0.04, 0.02, 0.02, 0.01)
PEAK_SCENARIOS = {
    "DESIGN_YELLOW_25MM": 25.0,
    "DESIGN_ORANGE_50MM": 50.0,
    "DESIGN_RED_100MM": 100.0,
    "DESIGN_CLOUDBURST_150MM": 150.0,
}
DEPTH_SCENARIOS = {f"DEPTH_{depth:g}MM_3H": depth for depth in (25.0, 50.0, 100.0, 150.0)}
EXPECTED_IDS = ("TS_2005_JULY26", *PEAK_SCENARIOS, *DEPTH_SCENARIOS)
CATALOG_COLUMNS = ("timeseries_id", "datetime", "rainfall_15min_mm", "intensity_mm_per_hr")
OUTPUT_NAMES = (
    "timeseries_2005_july26.dat",
    "timeseries_design_storms.dat",
    "timeseries_depth_scenarios.dat",
    "swmm_rainfall_catalog.csv",
    "swmm_rainfall_metadata.json",
)


@dataclass(frozen=True)
class RainfallRecord:
    timeseries_id: str
    timestamp: datetime
    depth_mm: float

    def as_catalog_row(self) -> dict[str, object]:
        depth_precision = 3 if self.timeseries_id == "TS_2005_JULY26" else 6
        intensity_precision = 2 if self.timeseries_id == "TS_2005_JULY26" else 6
        return {
            "timeseries_id": self.timeseries_id,
            "datetime": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "rainfall_15min_mm": round(self.depth_mm, depth_precision),
            "intensity_mm_per_hr": round(self.depth_mm / INTERVAL_HOURS, intensity_precision),
        }


def normalized_profile() -> tuple[float, ...]:
    if len(PROFILE) != 12 or any(weight < 0 for weight in PROFILE):
        raise ValueError("The design profile must contain twelve non-negative weights")
    total = sum(PROFILE)
    if total <= 0:
        raise ValueError("The design profile must have a positive sum")
    return tuple(weight / total for weight in PROFILE)


def _records(series_id: str, start: datetime, depths: Iterable[float]) -> list[RainfallRecord]:
    return [
        RainfallRecord(series_id, start + timedelta(minutes=INTERVAL_MINUTES * index), round(float(depth), 6))
        for index, depth in enumerate(depths)
    ]


def generate_historical_records() -> list[RainfallRecord]:
    """Reconstruct 15-minute values from the existing 3-hour source totals."""
    source_blocks = (0.9, 0.0, 17.5, 431.7, 217.6, 101.2, 116.1, 11.0, 48.2)
    disaggregation = (0.02, 0.04, 0.06, 0.09, 0.13, 0.16, 0.16, 0.13, 0.09, 0.06, 0.04, 0.02)
    profile = tuple(weight / sum(disaggregation) for weight in disaggregation)
    records: list[RainfallRecord] = []
    start = datetime(2005, 7, 26)
    for block_index, block_depth in enumerate(source_blocks):
        block_start = start + timedelta(hours=3 * block_index)
        records.extend(_records("TS_2005_JULY26", block_start, (block_depth * weight for weight in profile)))
    return records


def generate_peak_records() -> list[RainfallRecord]:
    profile = normalized_profile()
    max_weight = max(profile)
    records: list[RainfallRecord] = []
    start = datetime(2026, 7, 1)
    for series_id, target_peak in PEAK_SCENARIOS.items():
        total_depth = target_peak / (4.0 * max_weight)
        records.extend(_records(series_id, start, (total_depth * weight for weight in profile)))
    return records


def generate_depth_records() -> list[RainfallRecord]:
    profile = normalized_profile()
    start = datetime(2026, 7, 1)
    return [
        record
        for series_id, target_depth in DEPTH_SCENARIOS.items()
        for record in _records(series_id, start, (target_depth * weight for weight in profile))
    ]


def generate_all_records() -> list[RainfallRecord]:
    return generate_historical_records() + generate_peak_records() + generate_depth_records()


def validate_records(records: list[RainfallRecord]) -> dict[str, object]:
    if not records:
        raise ValueError("Rainfall catalogue is empty")
    grouped: dict[str, list[RainfallRecord]] = {}
    for record in records:
        if record.timeseries_id not in EXPECTED_IDS:
            raise ValueError(f"Unexpected series ID: {record.timeseries_id}")
        if record.depth_mm < 0:
            raise ValueError(f"Negative rainfall depth in {record.timeseries_id}")
        grouped.setdefault(record.timeseries_id, []).append(record)
    if set(grouped) != set(EXPECTED_IDS):
        raise ValueError("Catalogue does not contain all expected series IDs")
    expected_lengths = {"TS_2005_JULY26": 108, **{series_id: 12 for series_id in EXPECTED_IDS if series_id != "TS_2005_JULY26"}}
    for series_id, series_records in grouped.items():
        if len(series_records) != expected_lengths[series_id]:
            raise ValueError(f"{series_id} has {len(series_records)} records")
        timestamps = [record.timestamp for record in series_records]
        if len(set(timestamps)) != len(timestamps):
            raise ValueError(f"Duplicate timestamp in {series_id}")
        if any(next_timestamp - timestamp != timedelta(minutes=15) for timestamp, next_timestamp in zip(timestamps, timestamps[1:])):
            raise ValueError(f"Non-15-minute spacing in {series_id}")
        if any(abs(record.depth_mm / INTERVAL_HOURS - round(record.depth_mm / INTERVAL_HOURS, 6)) > 1e-9 for record in series_records):
            raise ValueError(f"Invalid intensity conversion in {series_id}")
    historical_total = sum(record.depth_mm for record in grouped["TS_2005_JULY26"])
    if abs(historical_total - 944.2) > 0.01:
        raise ValueError(f"Historical total is {historical_total}, expected approximately 944.2")
    profile = normalized_profile()
    peak_results = {
        series_id: {"peak_intensity_mm_per_hr": max(record.depth_mm / INTERVAL_HOURS for record in grouped[series_id]), "target_peak_intensity_mm_per_hr": target}
        for series_id, target in PEAK_SCENARIOS.items()
    }
    depth_results = {
        series_id: {"total_depth_mm": sum(record.depth_mm for record in grouped[series_id]), "target_total_depth_mm": target}
        for series_id, target in DEPTH_SCENARIOS.items()
    }
    for result in peak_results.values():
        if abs(result["peak_intensity_mm_per_hr"] - result["target_peak_intensity_mm_per_hr"]) > 0.00001:
            raise ValueError("Peak-intensity target failed")
    for result in depth_results.values():
        if abs(result["total_depth_mm"] - result["target_total_depth_mm"]) > 0.00001:
            raise ValueError("Total-depth target failed")
    return {
        "record_count": len(records),
        "historical_total_mm": historical_total,
        "profile_sum": sum(profile),
        "peak_scenarios": peak_results,
        "depth_scenarios": depth_results,
    }


def _dat_lines(records: list[RainfallRecord], title: str) -> list[str]:
    return [title, "; Format: Series_Name Date Time Interval_Depth_mm"] + [
        f"{record.timeseries_id} {record.timestamp:%m/%d/%Y} {record.timestamp:%H:%M} {record.depth_mm:.6f}"
        for record in records
    ]


def build_outputs(records: list[RainfallRecord], validation: dict[str, object], generated_at: str) -> dict[str, str]:
    grouped: dict[str, list[RainfallRecord]] = {}
    for record in records:
        grouped.setdefault(record.timeseries_id, []).append(record)
    catalog_lines = [",".join(CATALOG_COLUMNS)]
    catalog_lines.extend(",".join(str(row[column]) for column in CATALOG_COLUMNS) for row in (record.as_catalog_row() for record in records))
    metadata = {
        "generated_at_utc": generated_at,
        "interval_minutes": INTERVAL_MINUTES,
        "scenario_duration_hours": 3,
        "units": {"rainfall_15min_mm": "mm depth per interval", "intensity_mm_per_hr": "mm/hour interval-average"},
        "profile": list(normalized_profile()),
        "source_data_limitations": "TS_2005_JULY26 is a synthetic temporal disaggregation of 3-hour source totals; its 15-minute values are not observed measurements.",
        "scenarios": {
            "TS_2005_JULY26": {"family": "historical_representation", "classification": "source-derived temporal reconstruction", "records": 108},
            **{series_id: {"family": "peak_intensity", "classification": "synthetic design scenario", "target_peak_intensity_mm_per_hr": target, "records": 12} for series_id, target in PEAK_SCENARIOS.items()},
            **{series_id: {"family": "total_depth", "classification": "synthetic design scenario", "target_total_depth_mm": target, "records": 12} for series_id, target in DEPTH_SCENARIOS.items()},
        },
        "validation": validation,
    }
    return {
        "timeseries_2005_july26.dat": "\n".join(_dat_lines(grouped["TS_2005_JULY26"], "; Synthetic 15-minute reconstruction of Mumbai 26 July 2005 rainfall; not observed 15-minute data")) + "\n",
        "timeseries_design_storms.dat": "\n".join(_dat_lines([record for series_id in PEAK_SCENARIOS for record in grouped[series_id]], "; Synthetic peak-intensity design scenarios; not observed rainfall")) + "\n",
        "timeseries_depth_scenarios.dat": "\n".join(_dat_lines([record for series_id in DEPTH_SCENARIOS for record in grouped[series_id]], "; Synthetic three-hour total-depth design scenarios; not observed rainfall")) + "\n",
        "swmm_rainfall_catalog.csv": "\n".join(catalog_lines) + "\n",
        "swmm_rainfall_metadata.json": json.dumps(metadata, indent=2) + "\n",
    }


def write_outputs(output_dir: Path, dry_run: bool = False) -> dict[str, object]:
    records = generate_all_records()
    validation = validate_records(records)
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    outputs = build_outputs(records, validation, generated_at)
    paths = [output_dir / name for name in OUTPUT_NAMES]
    if dry_run:
        return {"written": False, "paths": [str(path) for path in paths], "validation": validation}
    output_dir.mkdir(parents=True, exist_ok=True)
    # Keep staging on the destination volume so Windows os.replace is atomic.
    with tempfile.TemporaryDirectory(prefix=".rainfall-", dir=output_dir) as temp_name:
        temp_dir = Path(temp_name)
        staged = {name: temp_dir / name for name in OUTPUT_NAMES}
        for name, content in outputs.items():
            staged[name].write_text(content, encoding="utf-8", newline="\n")
        backups: dict[Path, Path] = {}
        try:
            for path in paths:
                if path.exists():
                    backup = temp_dir / f"{path.name}.bak"
                    shutil.copy2(path, backup)
                    backups[path] = backup
            for path in paths:
                os.replace(staged[path.name], path)
        except Exception:
            for path in paths:
                backup = backups.get(path)
                if backup and backup.exists():
                    os.replace(backup, path)
            raise
    return {"written": True, "paths": [str(path) for path in paths], "validation": validation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "swmm_ready")
    parser.add_argument("--dry-run", action="store_true", help="Validate and list outputs without writing files")
    args = parser.parse_args()
    result = write_outputs(args.output_dir, args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
