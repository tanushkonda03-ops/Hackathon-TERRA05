"""Run the controlled Ward L ALLOW_PONDING sensitivity experiment.

Reproduce from the repository root with:
    python scripts/run_swmm_sensitivity.py

This is a sensitivity experiment, not calibration or validation. The original
models/ward_L_kurla.inp, .rpt, and .out are read-only inputs; all run artifacts
are written under models/sensitivity/allow_ponding/.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

try:
    from pyswmm import Output, Simulation
except ImportError as exc:
    raise SystemExit(
        "PySWMM is required to run and parse this experiment, but is unavailable "
        f"in this Python environment: {exc}"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
BASELINE_INP = ROOT / "models" / "ward_L_kurla.inp"
EXPERIMENT_DIR = ROOT / "models" / "sensitivity" / "allow_ponding"
OPTION_PATTERN = re.compile(
    rb"(?im)^([ \t]*ALLOW_PONDING[ \t]+)YES([ \t]*(?:;[^\r\n]*)?)(\r?)$"
)
DIAGNOSTIC_PATTERN = re.compile(r"^\s*(WARNING|ERROR)\s+\d+:.*$", re.IGNORECASE)

CSV_FIELDS = [
    "experiment",
    "case",
    "allow_ponding",
    "simulation_status",
    "total_node_flooding_volume_ml",
    "total_node_flooding_volume_m3",
    "flooded_node_count",
    "max_node_depth_m",
    "max_depth_node_id",
    "max_ponded_depth_m",
    "max_ponded_depth_node_id",
    "peak_conduit_flow_cms",
    "peak_flow_conduit_id",
    "max_conduit_velocity_m_s",
    "max_velocity_conduit_id",
    "peak_outfall_discharge_cms",
    "peak_outfall_node_id",
    "total_outfall_discharge_ml",
    "total_outfall_discharge_m3",
    "runoff_continuity_error_pct",
    "routing_continuity_error_pct",
    "final_stored_volume_ml",
    "most_affected_node_id",
    "most_affected_node_flood_volume_ml",
    "most_affected_conduit_id",
    "warnings",
    "errors",
]


def _table_rows(report: str, heading: str, header_test) -> list[list[str]]:
    lines = report.splitlines()
    heading_index = next(
        (i for i, line in enumerate(lines) if line.strip() == heading), None
    )
    if heading_index is None:
        return []

    header_index = next(
        (
            i
            for i in range(heading_index + 1, len(lines))
            if header_test(" ".join(lines[i : i + 3]))
        ),
        None,
    )
    if header_index is None:
        return []

    divider_index = next(
        (
            i
            for i in range(header_index + 1, len(lines))
            if re.match(r"^\s*-{3,}\s*$", lines[i])
        ),
        None,
    )
    if divider_index is None:
        return []

    rows = []
    for line in lines[divider_index + 1 :]:
        if not line.strip() or re.match(r"^\s*-{3,}\s*$", line):
            break
        rows.append(line.split())
    return rows


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def _max_row(rows: list[list[str]], value_index: int):
    parsed = []
    for row in rows:
        try:
            parsed.append((row[0], _number(row[value_index])))
        except (IndexError, ValueError):
            continue
    return max(parsed, key=lambda item: item[1]) if parsed else ("", "")


def _continuity_error(section: str) -> str:
    match = re.search(
        r"Continuity Error \(%\)\s*\.{3,}\s*([+-]?\d+(?:\.\d+)?)", section
    )
    return match.group(1) if match else ""


def _extract_metrics(report_path: Path, output_path: Path) -> dict:
    report = report_path.read_text(errors="replace")

    # Verify that SWMM's binary output is readable and has model objects.
    with Output(str(output_path)) as output:
        if not output.nodes or not output.links:
            raise RuntimeError("SWMM binary output contains no nodes or links")

    flooding = _table_rows(
        report,
        "Node Flooding Summary",
        lambda line: "Node" in line and "Flooded" in line and "Meters" in line,
    )
    depths = _table_rows(
        report,
        "Node Depth Summary",
        lambda line: "Node" in line and "Type" in line and "Meters" in line,
    )
    links = _table_rows(
        report,
        "Link Flow Summary",
        lambda line: "Link" in line and "Type" in line and "CMS" in line,
    )
    outfalls = _table_rows(
        report,
        "Outfall Loading Summary",
        lambda line: "Outfall Node" in line and "Pcnt" in line and "CMS" in line,
    )

    flooding_values = []
    for row in flooding:
        try:
            flooding_values.append((row[0], _number(row[-2]), _number(row[-1])))
        except (IndexError, ValueError):
            continue

    max_depth = _max_row(depths, 3)
    max_flood = max(flooding_values, key=lambda row: row[1]) if flooding_values else ("", 0.0, 0.0)
    max_ponding = max(flooding_values, key=lambda row: row[2]) if flooding_values else ("", 0.0, 0.0)
    peak_flow = _max_row(links, 2)
    max_velocity = _max_row(links, 5)
    peak_outfall = _max_row(outfalls, 3)

    total_flood_ml = sum(row[1] for row in flooding_values)
    total_outfall_ml = sum(_number(row[4]) for row in outfalls if len(row) >= 5)
    runoff_section = report.split("Runoff Quantity Continuity", 1)[-1].split(
        "Flow Routing Continuity", 1
    )[0]
    routing_section = report.split("Flow Routing Continuity", 1)[-1].split(
        "Highest Continuity Errors", 1
    )[0]
    final_storage = re.search(
        r"Final Stored Volume\s*\.\.\.\s*[+-]?[\d.]+\s+([+-]?[\d.]+)",
        routing_section,
    )

    diagnostics = [line.strip() for line in report.splitlines() if DIAGNOSTIC_PATTERN.match(line)]
    return {
        "total_node_flooding_volume_ml": total_flood_ml,
        "total_node_flooding_volume_m3": total_flood_ml * 1000.0,
        "flooded_node_count": len(flooding_values),
        "max_node_depth_m": max_depth[1],
        "max_depth_node_id": max_depth[0],
        "max_ponded_depth_m": max_ponding[2],
        "max_ponded_depth_node_id": max_ponding[0],
        "peak_conduit_flow_cms": peak_flow[1],
        "peak_flow_conduit_id": peak_flow[0],
        "max_conduit_velocity_m_s": max_velocity[1],
        "max_velocity_conduit_id": max_velocity[0],
        "peak_outfall_discharge_cms": peak_outfall[1],
        "peak_outfall_node_id": peak_outfall[0],
        "total_outfall_discharge_ml": total_outfall_ml,
        "total_outfall_discharge_m3": total_outfall_ml * 1000.0,
        "runoff_continuity_error_pct": _continuity_error(runoff_section),
        "routing_continuity_error_pct": _continuity_error(routing_section),
        "final_stored_volume_ml": _number(final_storage.group(1)) if final_storage else "",
        "most_affected_node_id": max_flood[0],
        "most_affected_node_flood_volume_ml": max_flood[1],
        "most_affected_conduit_id": peak_flow[0],
        "warnings": " | ".join(line for line in diagnostics if line.upper().startswith("WARNING")),
        "errors": " | ".join(line for line in diagnostics if line.upper().startswith("ERROR")),
    }


def _run_case(case: str, allow_ponding: str, input_bytes: bytes) -> dict:
    case_dir = EXPERIMENT_DIR / case
    case_dir.mkdir(parents=True, exist_ok=True)
    inp_path = case_dir / "ward_L_kurla.inp"
    rpt_path = case_dir / "ward_L_kurla.rpt"
    out_path = case_dir / "ward_L_kurla.out"
    inp_path.write_bytes(input_bytes)

    record = {
        "experiment": "ALLOW_PONDING sensitivity; not calibration or validation",
        "case": case,
        "allow_ponding": allow_ponding,
        "simulation_status": "complete",
    }
    try:
        Simulation(str(inp_path), str(rpt_path), str(out_path)).execute()
        record.update(_extract_metrics(rpt_path, out_path))
        if record["errors"]:
            record["simulation_status"] = "completed_with_SWMM_errors"
    except Exception as exc:
        record["simulation_status"] = "failed"
        record["errors"] = f"{type(exc).__name__}: {exc}"
        if rpt_path.exists():
            diagnostics = [
                line.strip()
                for line in rpt_path.read_text(errors="replace").splitlines()
                if DIAGNOSTIC_PATTERN.match(line)
            ]
            record["warnings"] = " | ".join(
                line for line in diagnostics if line.upper().startswith("WARNING")
            )
            swmm_errors = [
                line for line in diagnostics if line.upper().startswith("ERROR")
            ]
            if swmm_errors:
                record["errors"] += " | " + " | ".join(swmm_errors)
    return record


def main() -> int:
    if not BASELINE_INP.is_file():
        raise SystemExit(f"Baseline INP not found: {BASELINE_INP}")

    baseline_bytes = BASELINE_INP.read_bytes()
    matches = list(OPTION_PATTERN.finditer(baseline_bytes))
    if len(matches) != 1:
        raise SystemExit(
            "Expected exactly one ALLOW_PONDING YES setting in the baseline INP; "
            f"found {len(matches)}. No simulation was run."
        )
    candidate_bytes, replacements = OPTION_PATTERN.subn(rb"\1NO\2\3", baseline_bytes)
    if replacements != 1:
        raise SystemExit("Could not create the single-option candidate INP")

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = _run_case("baseline", "YES", baseline_bytes)
    candidate = _run_case("candidate_allow_ponding_no", "NO", candidate_bytes)

    csv_path = EXPERIMENT_DIR / "baseline_vs_candidate.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows((baseline, candidate))

    print(f"Sensitivity experiment CSV: {csv_path}")
    for record in (baseline, candidate):
        warning_count = len(record.get("warnings", "").split(" | ")) if record.get("warnings") else 0
        print(
            f"{record['case']}: {record['simulation_status']}; "
            f"warnings={warning_count}; errors={record.get('errors', '') or 'none'}"
        )
    return 0 if all(record["simulation_status"] == "complete" for record in (baseline, candidate)) else 1


if __name__ == "__main__":
    sys.exit(main())