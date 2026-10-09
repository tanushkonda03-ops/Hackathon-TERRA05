"""Run the controlled Ward L conduit Manning roughness sensitivity experiment.

Reproduce from the repository root with:
    python scripts/run_swmm_roughness_sensitivity.py

All experiment inputs and outputs are isolated under
models/sensitivity/conduit_roughness/. This is sensitivity analysis, not
calibration or validation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from pyswmm import Simulation
    from run_swmm_sensitivity import _extract_metrics
except ImportError as exc:
    raise SystemExit(
        "PySWMM and the existing SWMM report/output parser are required, but "
        f"could not be imported: {exc}"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
BASELINE_INP = ROOT / "models" / "ward_L_kurla.inp"
EXPERIMENT_DIR = ROOT / "models" / "sensitivity" / "conduit_roughness"
RUN_LOG = EXPERIMENT_DIR / "run_log.txt"
SCENARIOS = (
    ("baseline", 1.0),
    ("lower_roughness", 0.8),
    ("higher_roughness", 1.2),
)
PROTECTED_FILES = (
    ROOT / "models" / "ward_L_kurla.inp",
    ROOT / "models" / "ward_L_kurla.rpt",
    ROOT / "models" / "ward_L_kurla.out",
)
CONDUIT_ROW = re.compile(rb"^([ \t]*\S+(?:[ \t]+\S+){3}[ \t]+)(\S+)(.*)$")

CSV_FIELDS = [
    "scenario_name",
    "roughness_multiplier",
    "simulation_status",
    "comparison_eligible",
    "conduits_changed",
    "roughness_min",
    "roughness_max",
    "swmm_errors",
    "warnings",
    "total_node_flooding_volume_ml",
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
    "runoff_continuity_error_pct",
    "routing_continuity_error_pct",
    "final_stored_volume_ml",
    "most_affected_node_id",
    "most_affected_node_flood_volume_ml",
    "baseline_reference_check",
]


def _rewrite_conduit_roughness(
    data: bytes, multiplier: float | None
) -> tuple[bytes, list[tuple[str, float, float]]]:
    lines = data.splitlines(keepends=True)
    in_conduits = False
    records = []
    rewritten = []

    for line in lines:
        section = line.strip().upper()
        if section.startswith(b"[") and section.endswith(b"]"):
            in_conduits = section == b"[CONDUITS]"
            rewritten.append(line)
            continue
        if not in_conduits or not line.strip() or line.lstrip().startswith(b";"):
            rewritten.append(line)
            continue

        content = line.rstrip(b"\r\n")
        match = CONDUIT_ROW.match(content)
        if not match:
            raise ValueError(f"Could not parse conduit row: {line[:120]!r}")
        prefix, roughness_bytes, suffix = match.groups()
        conduit_id = prefix.split()[0].decode("ascii")
        original = float(roughness_bytes)
        updated = original if multiplier is None else original * multiplier
        replacement = b"__ROUGHNESS__" if multiplier is None else (
            roughness_bytes if multiplier == 1.0 else format(updated, ".10g").encode("ascii")
        )
        records.append((conduit_id, original, updated))
        newline = line[len(content) :]
        rewritten.append(prefix + replacement + suffix + newline)

    if not records:
        raise ValueError("No conduit rows found in the [CONDUITS] section")
    return b"".join(rewritten), records


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_case(scenario: str, multiplier: float, baseline_bytes: bytes) -> dict:
    if multiplier == 1.0:
        candidate_bytes = baseline_bytes
        records = _rewrite_conduit_roughness(baseline_bytes, None)[1]
    else:
        candidate_bytes, records = _rewrite_conduit_roughness(baseline_bytes, multiplier)

    masked_baseline, baseline_records = _rewrite_conduit_roughness(baseline_bytes, None)
    masked_candidate, candidate_records = _rewrite_conduit_roughness(candidate_bytes, None)
    if masked_baseline != masked_candidate:
        raise ValueError(f"{scenario} INP differs outside conduit roughness fields")
    if [row[0] for row in baseline_records] != [row[0] for row in candidate_records]:
        raise ValueError(f"{scenario} INP changed conduit IDs or row order")

    changed = sum(original != updated for _, original, updated in records)
    if multiplier != 1.0 and changed != len(records):
        raise ValueError(
            f"Expected every conduit roughness to change for {scenario}; changed {changed}"
        )

    candidate_rows = _rewrite_conduit_roughness(candidate_bytes, None)[1]
    values = [row[1] for row in candidate_rows]
    input_path = EXPERIMENT_DIR / scenario / "ward_L_kurla.inp"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(candidate_bytes)
    if input_path.read_bytes() != candidate_bytes:
        raise IOError(f"Could not verify written input for {scenario}")

    return {
        "scenario_name": scenario,
        "roughness_multiplier": multiplier,
        "conduits_changed": changed,
        "roughness_min": min(values),
        "roughness_max": max(values),
        "input_path": input_path,
        "roughness_only_verified": True,
    }


def _baseline_check(metrics: dict) -> str:
    checks = (
        ("total_node_flooding_volume_ml", 636.459, 0.0011),
        ("flooded_node_count", 208, 0),
        ("runoff_continuity_error_pct", -0.084, 0.001),
        ("routing_continuity_error_pct", -0.058, 0.001),
    )
    discrepancies = []
    for name, expected, tolerance in checks:
        actual = metrics[name]
        if actual == "" or abs(float(actual) - expected) > tolerance:
            discrepancies.append(f"{name}: expected {expected}, observed {actual}")
    return "PASS" if not discrepancies else "DISCREPANCY: " + "; ".join(discrepancies)


def _run_case(case: dict) -> dict:
    scenario = case["scenario_name"]
    case_dir = case["input_path"].parent
    report_path = case_dir / "ward_L_kurla.rpt"
    output_path = case_dir / "ward_L_kurla.out"
    for old_output in (report_path, output_path):
        if old_output.exists():
            old_output.unlink()

    row = {
        "scenario_name": scenario,
        "roughness_multiplier": case["roughness_multiplier"],
        "simulation_status": "incomplete",
        "comparison_eligible": "false",
        "conduits_changed": case["conduits_changed"],
        "roughness_min": case["roughness_min"],
        "roughness_max": case["roughness_max"],
        "swmm_errors": "",
        "warnings": "",
    }
    try:
        Simulation(str(case["input_path"]), str(report_path), str(output_path)).execute()
        if not report_path.is_file() or not output_path.is_file():
            raise RuntimeError("SWMM did not produce both report and binary output files")
        report_text = report_path.read_text(errors="replace")
        if "Analysis begun on:" not in report_text or "Analysis ended on:" not in report_text:
            raise RuntimeError("SWMM report lacks complete analysis start/end markers")

        metrics = _extract_metrics(report_path, output_path)
        row.update(
            {
                "total_node_flooding_volume_ml": metrics["total_node_flooding_volume_ml"],
                "flooded_node_count": metrics["flooded_node_count"],
                "max_node_depth_m": metrics["max_node_depth_m"],
                "max_depth_node_id": metrics["max_depth_node_id"],
                "max_ponded_depth_m": metrics["max_ponded_depth_m"],
                "max_ponded_depth_node_id": metrics["max_ponded_depth_node_id"],
                "peak_conduit_flow_cms": metrics["peak_conduit_flow_cms"],
                "peak_flow_conduit_id": metrics["peak_flow_conduit_id"],
                "max_conduit_velocity_m_s": metrics["max_conduit_velocity_m_s"],
                "max_velocity_conduit_id": metrics["max_velocity_conduit_id"],
                "peak_outfall_discharge_cms": metrics["peak_outfall_discharge_cms"],
                "peak_outfall_node_id": metrics["peak_outfall_node_id"],
                "total_outfall_discharge_ml": metrics["total_outfall_discharge_ml"],
                "runoff_continuity_error_pct": metrics["runoff_continuity_error_pct"],
                "routing_continuity_error_pct": metrics["routing_continuity_error_pct"],
                "final_stored_volume_ml": metrics["final_stored_volume_ml"],
                "most_affected_node_id": metrics["most_affected_node_id"],
                "most_affected_node_flood_volume_ml": metrics["most_affected_node_flood_volume_ml"],
                "warnings": metrics["warnings"],
                "swmm_errors": metrics["errors"],
            }
        )
        required = (
            "max_node_depth_m", "max_depth_node_id", "max_ponded_depth_m",
            "peak_conduit_flow_cms", "peak_flow_conduit_id", "max_conduit_velocity_m_s",
            "max_velocity_conduit_id", "peak_outfall_discharge_cms", "peak_outfall_node_id",
            "total_outfall_discharge_ml", "runoff_continuity_error_pct",
            "routing_continuity_error_pct", "final_stored_volume_ml",
        )
        missing = [name for name in required if row.get(name, "") == ""]
        if missing:
            raise RuntimeError("Parsed output is missing required metrics: " + ", ".join(missing))
        row["simulation_status"] = "complete" if not row["swmm_errors"] else "completed_with_swmm_errors"
        row["comparison_eligible"] = "true" if row["simulation_status"] == "complete" else "false"
    except KeyboardInterrupt:
        row["simulation_status"] = "incomplete_interrupted"
        row["swmm_errors"] = "Interrupted during SWMM execution"
    except Exception as exc:
        row["simulation_status"] = "incomplete"
        row["swmm_errors"] = f"{type(exc).__name__}: {exc}"
        if report_path.is_file():
            report_text = report_path.read_text(errors="replace")
            diagnostics = re.findall(r"^\s*(?:WARNING|ERROR)\s+\d+:.*$", report_text, re.M | re.I)
            row["warnings"] = " | ".join(line.strip() for line in diagnostics if "WARNING" in line.upper())
            errors = [line.strip() for line in diagnostics if "ERROR" in line.upper()]
            if errors:
                row["swmm_errors"] += " | " + " | ".join(errors)
    return row


def main() -> int:
    if not BASELINE_INP.is_file():
        raise SystemExit(f"Baseline INP not found: {BASELINE_INP}")
    if any(not path.is_file() for path in PROTECTED_FILES):
        raise SystemExit("One or more protected baseline INP/RPT/OUT files are missing")

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    original_hashes_before = {path.name: _sha256(path) for path in PROTECTED_FILES}
    baseline_bytes = BASELINE_INP.read_bytes()
    case_specs = [_input_case(name, multiplier, baseline_bytes) for name, multiplier in SCENARIOS]
    log_lines = [
        "Ward L conduit roughness sensitivity analysis; not calibration or validation.",
        f"Baseline INP SHA-256: {original_hashes_before['ward_L_kurla.inp']}",
    ]

    rows = []
    for case in case_specs:
        log_lines.append(
            f"Verified input: {case['scenario_name']}; multiplier={case['roughness_multiplier']}; "
            f"changed={case['conduits_changed']}; roughness_min={case['roughness_min']}; "
            f"roughness_max={case['roughness_max']}; roughness-only=True"
        )
    RUN_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    for case in case_specs:
        print(f"Running {case['scenario_name']} (roughness x{case['roughness_multiplier']})")
        row = _run_case(case)
        if row["scenario_name"] == "baseline" and row["simulation_status"] == "complete":
            row["baseline_reference_check"] = _baseline_check(row)
        rows.append(row)
        log_lines.append(
            f"{row['scenario_name']}: {row['simulation_status']}; "
            f"eligible={row['comparison_eligible']}; errors={row['swmm_errors'] or 'none'}"
        )
        RUN_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    csv_path = EXPERIMENT_DIR / "roughness_sensitivity_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    original_hashes_after = {path.name: _sha256(path) for path in PROTECTED_FILES}
    hashes_unchanged = original_hashes_before == original_hashes_after
    manifest = {
        "experiment": "conduit Manning roughness sensitivity analysis",
        "interpretation": "Sensitivity analysis only; not calibration or validation.",
        "baseline_reference": {
            "node_flooding_volume_ml": 636.459,
            "flooded_node_count": 208,
            "runoff_continuity_error_pct": -0.084,
            "routing_continuity_error_pct": -0.058,
        },
        "protected_original_hashes_before": original_hashes_before,
        "protected_original_hashes_after": original_hashes_after,
        "protected_originals_unchanged": hashes_unchanged,
        "inputs": [
            {
                "scenario_name": case["scenario_name"],
                "roughness_multiplier": case["roughness_multiplier"],
                "conduits_changed": case["conduits_changed"],
                "roughness_min": case["roughness_min"],
                "roughness_max": case["roughness_max"],
                "roughness_only_verified": case["roughness_only_verified"],
                "input_path": str(case["input_path"].relative_to(ROOT)),
            }
            for case in case_specs
        ],
        "simulation_statuses": {row["scenario_name"]: row["simulation_status"] for row in rows},
        "baseline_reference_check": next(
            (row.get("baseline_reference_check", "NOT_CHECKED_INCOMPLETE") for row in rows if row["scenario_name"] == "baseline"),
            "NOT_CHECKED",
        ),
        "comparison_csv": str(csv_path.relative_to(ROOT)),
    }
    (EXPERIMENT_DIR / "artifact_integrity.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    log_lines.append(f"Protected original INP/RPT/OUT hashes unchanged: {hashes_unchanged}")
    log_lines.append(f"Comparison CSV: {csv_path}")
    RUN_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(f"Comparison CSV: {csv_path}")
    print(f"Protected original hashes unchanged: {hashes_unchanged}")
    for row in rows:
        print(
            f"{row['scenario_name']}: {row['simulation_status']}; "
            f"eligible={row['comparison_eligible']}; "
            f"flooding={row.get('total_node_flooding_volume_ml', 'n/a')} ML; "
            f"flooded_nodes={row.get('flooded_node_count', 'n/a')}; "
            f"errors={row['swmm_errors'] or 'none'}"
        )
    if not hashes_unchanged:
        return 1
    return 0 if all(row["simulation_status"] == "complete" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())