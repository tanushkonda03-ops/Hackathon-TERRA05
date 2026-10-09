"""Build and run the isolated 24-hour Ward L rainfall candidate.

Run from the repository root:
    python scripts/run_rainfall_24h_candidate.py

This follows the requested eight-increment window; it is not calibration or
validation and does not independently verify the historical rainfall total.
"""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pyswmm import Simulation
    from rainfall_hyetograph import disaggregate_3h_intervals, render_swmm_series
    from run_swmm_sensitivity import _extract_metrics
except ImportError as exc:
    raise SystemExit(f"PySWMM and the local rainfall/report helpers are required: {exc}") from exc


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
BASELINE_INP = ROOT / "models" / "ward_L_kurla.inp"
BASELINE_RPT = ROOT / "models" / "ward_L_kurla.rpt"
BASELINE_OUT = ROOT / "models" / "ward_L_kurla.out"
LEGACY_RAIN = ROOT / "data" / "swmm_ready" / "timeseries_2005_july26.dat"
OBSERVATIONS = ROOT / "data" / "processed" / "rainfall_observations_v1.csv"
EVENT_BUILDER = SCRIPT_DIR / "build_rainfall_events.py"
FEATURE_BUILDER = SCRIPT_DIR / "build_rainfall_feature.py"
CANDIDATE_DIR = ROOT / "models" / "candidates" / "rainfall_24h"
CANDIDATE_INP = CANDIDATE_DIR / "ward_L_kurla_rainfall_24h.inp"
CANDIDATE_RPT = CANDIDATE_DIR / "ward_L_kurla_rainfall_24h.rpt"
CANDIDATE_OUT = CANDIDATE_DIR / "ward_L_kurla_rainfall_24h.out"
RUN_LOG = CANDIDATE_DIR / "run.log"
COMPARISON_CSV = CANDIDATE_DIR / "baseline_vs_rainfall_24h_candidate.csv"
BASELINE_SERIES_ID = "TS_2005_JULY26"
CANDIDATE_SERIES_ID = "TS_2005_JULY26_24H_CANDIDATE"
DIAGNOSTIC_SERIES_ID = "TS_2005_JULY26_27H_DIAGNOSTIC"
TIMING_OPTIONS = {"START_DATE", "START_TIME", "REPORT_START_DATE", "REPORT_START_TIME"}

CSV_FIELDS = [
    "scenario",
    "simulation_status",
    "comparison_eligible",
    "rainfall_series_id",
    "rainfall_start",
    "rainfall_end",
    "rainfall_duration_hours",
    "rainfall_timestep_minutes",
    "rainfall_intervals",
    "rainfall_total_mm",
    "node_flooding_volume_ml",
    "flooded_node_count",
    "max_node_depth_m",
    "max_depth_node_id",
    "max_ponded_depth_m",
    "max_ponded_depth_node_id",
    "peak_conduit_flow_cms",
    "peak_flow_conduit_id",
    "peak_outfall_discharge_cms",
    "peak_outfall_node_id",
    "runoff_continuity_error_pct",
    "routing_continuity_error_pct",
    "final_stored_volume_ml",
    "most_affected_node_id",
    "most_affected_node_flood_volume_ml",
    "swmm_errors",
    "warnings",
]


def _read_observations() -> list[dict[str, str]]:
    with OBSERVATIONS.open(newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.DictReader(file) if row.get("event_id") == "E001"]
    rows.sort(key=lambda row: (row["observation_date"], row["observation_time_utc"]))
    return rows


def _observed_blocks(rows: list[dict[str, str]]) -> list[tuple[datetime, datetime, float]]:
    blocks = []
    for row in rows:
        end = datetime.strptime(
            row["observation_date"] + " " + row["observation_time_utc"], "%Y-%m-%d %H:%M"
        )
        if int(row["accumulation_period_hours"]) != 3:
            raise ValueError("E001 contains an unexpected accumulation period")
        blocks.append((end - timedelta(hours=3), end, float(row["rainfall_mm"])))
    expected_start = datetime(2005, 7, 26, 3)
    expected_end = datetime(2005, 7, 27, 3)
    if len(blocks) != 9 or blocks[0][1] != expected_start or blocks[-1][1] != expected_end:
        raise ValueError("E001 observation rows do not match the expected nine-record local table")
    if round(sum(block[2] for block in blocks[1:]), 1) != 943.3:
        raise ValueError("The eight selected local increments do not sum to 943.3 mm")
    return blocks


def _parse_series(path: Path, series_id: str) -> list[tuple[datetime, float]]:
    records = []
    for line in path.read_text(errors="replace").splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[0] == series_id:
            records.append(
                (
                    datetime.strptime(fields[1] + " " + fields[2], "%m/%d/%Y %H:%M"),
                    float(fields[3]),
                )
            )
    return records


def _series_rows(series_id: str, records: list[tuple[datetime, float]]) -> list[str]:
    rendered = render_swmm_series(series_id, records, "candidate rainfall series")
    return rendered.splitlines()[2:]


def _write_series_files(blocks: list[tuple[datetime, datetime, float]]) -> tuple[list, list]:
    legacy_records = disaggregate_3h_intervals(blocks)
    candidate_records = disaggregate_3h_intervals(blocks[1:], conserve_block_totals=True)
    if legacy_records != _parse_series(LEGACY_RAIN, BASELINE_SERIES_ID):
        raise ValueError("Reconstructed 27-hour diagnostic does not match the preserved baseline rainfall file")
    if len(candidate_records) != 96 or round(sum(value for _, value in candidate_records), 3) != 943.3:
        raise ValueError("Corrected candidate series failed the 96-interval / 943.3 mm check")

    candidate_path = ROOT / "data" / "swmm_ready" / "timeseries_2005_july26_24h_candidate.dat"
    diagnostic_path = ROOT / "data" / "swmm_ready" / "timeseries_2005_july26_27h_diagnostic.dat"
    candidate_path.write_text(
        render_swmm_series(
            CANDIDATE_SERIES_ID,
            candidate_records,
            "24-hour local candidate: eight 3-hour increments; 943.3 mm arithmetic total; not historical verification",
        ),
        encoding="utf-8",
    )
    diagnostic_path.write_text(
        render_swmm_series(
            DIAGNOSTIC_SERIES_ID,
            legacy_records,
            "27-hour diagnostic reconstruction: nine 3-hour increments; 944.2 mm",
        ),
        encoding="utf-8",
    )
    return candidate_records, legacy_records


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s*\[([^]]+)\]", line)
        if match:
            current = match.group(1).upper()
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return sections


def _build_candidate_inp(candidate_records: list[tuple[datetime, float]]) -> None:
    original = BASELINE_INP.read_text(encoding="utf-8-sig")
    lines = original.splitlines(keepends=True)
    candidate_rows = _series_rows(CANDIDATE_SERIES_ID, candidate_records)
    output = []
    section = ""
    inserted_series = False
    replaced_gage = 0
    replaced_times = set()
    updated_title = 0

    for line in lines:
        match = re.match(r"^\s*\[([^]]+)\]", line)
        if match:
            section = match.group(1).upper()
            output.append(line)
            continue
        fields = line.split()
        if section == "OPTIONS" and len(fields) >= 2 and fields[0].upper() in TIMING_OPTIONS:
            key = fields[0].upper()
            value = "03:00:00" if key.endswith("TIME") else "07/26/2005"
            line = re.sub(r"^(\s*\S+\s+)\S+", lambda match: match.group(1) + value, line)
            replaced_times.add(key)
        elif section == "RAINGAGES" and BASELINE_SERIES_ID in line and "TIMESERIES" in line:
            line = line.replace(BASELINE_SERIES_ID, CANDIDATE_SERIES_ID)
            replaced_gage += 1
        elif section == "TITLE" and line.lstrip().startswith(";;Rainfall:"):
            line = re.sub(
                r"^\s*;;Rainfall:.*$",
                ";;Rainfall: 943.3 mm from eight local 3-hour increments in a 24-hour window; reconstructed at 15-minute resolution",
                line.rstrip("\r\n"),
            ) + ("\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else "")
            updated_title += 1
        elif section == "TIMESERIES" and fields and fields[0] == BASELINE_SERIES_ID:
            if not inserted_series:
                output.extend(row + "\n" for row in candidate_rows)
                inserted_series = True
            continue
        output.append(line)

    if replaced_gage != 1 or replaced_times != TIMING_OPTIONS or not inserted_series or updated_title != 1:
        raise ValueError(
            "Could not safely replace exactly the rainfall reference, series, title, and timing options"
        )
    candidate_text = "".join(output)
    candidate_gage = next(
        (line.split() for line in _sections(candidate_text).get("RAINGAGES", []) if "TIMESERIES" in line),
        [],
    )
    if not candidate_gage or candidate_gage[-1] != CANDIDATE_SERIES_ID:
        raise ValueError("Candidate raingage still references the legacy rainfall series")
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_INP.write_text(candidate_text, encoding="utf-8")

    if _normalized_inp(original) != _normalized_inp(candidate_text):
        raise ValueError("Candidate INP differs from baseline outside allowed rainfall/timing changes")


def _normalized_inp(text: str) -> list[str]:
    normalized = []
    section = ""
    series_marker_added = False
    for line in text.splitlines():
        match = re.match(r"^\s*\[([^]]+)\]", line)
        if match:
            section = match.group(1).upper()
            series_marker_added = False
            normalized.append(line)
            continue
        fields = line.split()
        if section == "OPTIONS" and len(fields) >= 2 and fields[0].upper() in TIMING_OPTIONS:
            normalized.append(f"{fields[0].upper()} <CANDIDATE_TIMING>")
        elif section == "TITLE" and line.lstrip().startswith(";;Rainfall:"):
            normalized.append(";;Rainfall: <CANDIDATE_RAINFALL_DESCRIPTION>")
        elif section == "RAINGAGES" and "TIMESERIES" in line:
            normalized.append(re.sub(r"TS_2005_JULY26(?:_24H_CANDIDATE)?", "<RAINFALL_SERIES>", line))
        elif section == "TIMESERIES" and fields and fields[0] in {BASELINE_SERIES_ID, CANDIDATE_SERIES_ID}:
            if not series_marker_added:
                normalized.append("<RAINFALL_SERIES_BLOCK>")
                series_marker_added = True
        else:
            normalized.append(line)
    return normalized


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {str(file.relative_to(path)): _sha256(file) for file in path.rglob("*") if file.is_file()}


def _run_builders() -> list[str]:
    logs = []
    for script in (EVENT_BUILDER, FEATURE_BUILDER):
        result = subprocess.run(
            [sys.executable, "-B", str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        logs.append(f"$ python {script.relative_to(ROOT)}\n{result.stdout.strip()}")
    return logs


def _rain_metadata(records: list[tuple[datetime, float]]) -> dict:
    intervals = sorted({right[0] - left[0] for left, right in zip(records, records[1:])})
    if len(intervals) != 1:
        raise ValueError("Rainfall timestep is not uniform")
    timestep = intervals[0]
    return {
        "start": records[0][0],
        "end": records[-1][0] + timestep,
        "duration_hours": len(records) * timestep.total_seconds() / 3600,
        "timestep_minutes": timestep.total_seconds() / 60,
        "intervals": len(records),
        "total_mm": sum(value for _, value in records),
    }


def _comparison_row(
    name: str, status: str, series_id: str, rainfall: dict, metrics: dict | None
) -> dict:
    row = {
        "scenario": name,
        "simulation_status": status,
        "comparison_eligible": "true" if metrics is not None and not metrics.get("errors") else "false",
        "rainfall_series_id": series_id,
        "rainfall_start": rainfall["start"].strftime("%Y-%m-%d %H:%M"),
        "rainfall_end": rainfall["end"].strftime("%Y-%m-%d %H:%M"),
        "rainfall_duration_hours": rainfall["duration_hours"],
        "rainfall_timestep_minutes": rainfall["timestep_minutes"],
        "rainfall_intervals": rainfall["intervals"],
        "rainfall_total_mm": rainfall["total_mm"],
    }
    if metrics:
        row.update(
            {
                "node_flooding_volume_ml": metrics["total_node_flooding_volume_ml"],
                "flooded_node_count": metrics["flooded_node_count"],
                "max_node_depth_m": metrics["max_node_depth_m"],
                "max_depth_node_id": metrics["max_depth_node_id"],
                "max_ponded_depth_m": metrics["max_ponded_depth_m"],
                "max_ponded_depth_node_id": metrics["max_ponded_depth_node_id"],
                "peak_conduit_flow_cms": metrics["peak_conduit_flow_cms"],
                "peak_flow_conduit_id": metrics["peak_flow_conduit_id"],
                "peak_outfall_discharge_cms": metrics["peak_outfall_discharge_cms"],
                "peak_outfall_node_id": metrics["peak_outfall_node_id"],
                "runoff_continuity_error_pct": metrics["runoff_continuity_error_pct"],
                "routing_continuity_error_pct": metrics["routing_continuity_error_pct"],
                "final_stored_volume_ml": metrics["final_stored_volume_ml"],
                "most_affected_node_id": metrics["most_affected_node_id"],
                "most_affected_node_flood_volume_ml": metrics["most_affected_node_flood_volume_ml"],
                "swmm_errors": metrics["errors"],
                "warnings": metrics["warnings"],
            }
        )
    return row


def main() -> int:
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    protected_files = [BASELINE_INP, BASELINE_RPT, BASELINE_OUT, OBSERVATIONS, LEGACY_RAIN]
    if any(not path.is_file() for path in protected_files):
        raise SystemExit("A required existing baseline or local rainfall input is missing")
    hashes_before = {str(path.relative_to(ROOT)): _sha256(path) for path in protected_files}
    ponding_hashes_before = _tree_hashes(ROOT / "models" / "sensitivity" / "allow_ponding")
    roughness_hashes_before = _tree_hashes(ROOT / "models" / "sensitivity" / "conduit_roughness")

    log_lines = [
        "Controlled rainfall-duration candidate; sensitivity/input-definition experiment, not calibration or validation.",
        "The raw rainfall_observations_v1.csv is read only and is not regenerated.",
    ]
    try:
        log_lines.extend(_run_builders())
        observations = _read_observations()
        blocks = _observed_blocks(observations)
        candidate_records, legacy_records = _write_series_files(blocks)
        _build_candidate_inp(candidate_records)
        log_lines.append(
            f"Candidate series: {len(candidate_records)} intervals, "
            f"{sum(value for _, value in candidate_records):.3f} mm; "
            f"legacy diagnostic: {len(legacy_records)} intervals, "
            f"{sum(value for _, value in legacy_records):.3f} mm."
        )
        log_lines.append("Candidate INP difference audit: PASS (rainfall series/reference/title and start/report timing only).")
    except Exception as exc:
        RUN_LOG.write_text("\n".join(log_lines + [f"Build failed: {type(exc).__name__}: {exc}"]) + "\n", encoding="utf-8")
        raise

    baseline_records = _parse_series(LEGACY_RAIN, BASELINE_SERIES_ID)
    candidate_series_path = ROOT / "data" / "swmm_ready" / "timeseries_2005_july26_24h_candidate.dat"
    candidate_records = _parse_series(candidate_series_path, CANDIDATE_SERIES_ID)
    baseline_rain = _rain_metadata(baseline_records)
    candidate_rain = _rain_metadata(candidate_records)

    baseline_metrics = _extract_metrics(BASELINE_RPT, BASELINE_OUT)
    baseline_status = "complete_existing_baseline"
    baseline_check = (
        abs(baseline_metrics["total_node_flooding_volume_ml"] - 636.459) <= 0.0011
        and baseline_metrics["flooded_node_count"] == 208
        and abs(float(baseline_metrics["runoff_continuity_error_pct"]) + 0.084) <= 0.001
        and abs(float(baseline_metrics["routing_continuity_error_pct"]) + 0.058) <= 0.001
    )
    if not baseline_check:
        log_lines.append("Baseline report differs from established reference metrics; see comparison CSV.")

    candidate_metrics = None
    candidate_status = "incomplete"
    candidate_errors = ""
    try:
        Simulation(str(CANDIDATE_INP), str(CANDIDATE_RPT), str(CANDIDATE_OUT)).execute()
        if not CANDIDATE_RPT.is_file() or not CANDIDATE_OUT.is_file():
            raise RuntimeError("SWMM did not create both candidate RPT and OUT files")
        report_text = CANDIDATE_RPT.read_text(errors="replace")
        if "Analysis begun on:" not in report_text or "Analysis ended on:" not in report_text:
            raise RuntimeError("Candidate RPT is missing complete-analysis markers")
        candidate_metrics = _extract_metrics(CANDIDATE_RPT, CANDIDATE_OUT)
        candidate_errors = candidate_metrics["errors"]
        candidate_status = "complete" if not candidate_errors else "completed_with_swmm_errors"
    except KeyboardInterrupt:
        candidate_status = "incomplete_interrupted"
        candidate_errors = "Interrupted during candidate SWMM execution"
    except Exception as exc:
        candidate_status = "incomplete"
        candidate_errors = f"{type(exc).__name__}: {exc}"

    rows = [
        _comparison_row("baseline_27h", baseline_status, BASELINE_SERIES_ID, baseline_rain, baseline_metrics),
        _comparison_row(
            "corrected_24h_candidate",
            candidate_status,
            CANDIDATE_SERIES_ID,
            candidate_rain,
            candidate_metrics,
        ),
    ]
    if candidate_metrics is None:
        rows[1]["swmm_errors"] = candidate_errors

    with COMPARISON_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    hashes_after = {str(path.relative_to(ROOT)): _sha256(path) for path in protected_files}
    ponding_hashes_after = _tree_hashes(ROOT / "models" / "sensitivity" / "allow_ponding")
    roughness_hashes_after = _tree_hashes(ROOT / "models" / "sensitivity" / "conduit_roughness")
    preserved = hashes_before == hashes_after
    experiments_preserved = (
        ponding_hashes_before == ponding_hashes_after
        and roughness_hashes_before == roughness_hashes_after
    )
    log_lines.extend(
        [
            f"Baseline reference metrics: {'PASS' if baseline_check else 'DISCREPANCY'}.",
            f"Candidate simulation status: {candidate_status}; errors: {candidate_errors or 'none'}.",
            f"Original model/raw observation/legacy series hashes unchanged: {preserved}.",
            f"Existing sensitivity experiments unchanged: {experiments_preserved}.",
            f"Comparison CSV: {COMPARISON_CSV}",
        ]
    )
    RUN_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(f"Candidate INP: {CANDIDATE_INP}")
    print(f"Comparison CSV: {COMPARISON_CSV}")
    print(f"Candidate status: {candidate_status}; errors: {candidate_errors or 'none'}")
    print(f"Preserved original and sensitivity artifacts: {preserved and experiments_preserved}")
    return 0 if candidate_status == "complete" and preserved and experiments_preserved and baseline_check else 1


if __name__ == "__main__":
    sys.exit(main())