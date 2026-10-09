"""Write a focused read-only Ward L rainfall/depth diagnostic report."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pyswmm import Output
    from swmm.toolkit.shared_enum import NodeAttribute
except ImportError as exc:
    raise SystemExit(f"PySWMM is required to read the existing SWMM .out: {exc}") from exc


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "models" / "diagnostics" / "next_priority.md"
BASELINE_INP = ROOT / "models" / "ward_L_kurla.inp"
BASELINE_RPT = ROOT / "models" / "ward_L_kurla.rpt"
BASELINE_OUT = ROOT / "models" / "ward_L_kurla.out"
GENERATED_RAIN = ROOT / "data" / "swmm_ready" / "timeseries_2005_july26.dat"
EVENTS_CSV = ROOT / "data" / "processed" / "mumbai_flood_events_v1.csv"
OBSERVATIONS_CSV = ROOT / "data" / "processed" / "rainfall_observations_v1.csv"
JUNCTIONS_CSV = ROOT / "data" / "swmm_ready" / "pilot_ward_L" / "swmm_junctions_ward_L.csv"
SERIES_ID = "TS_2005_JULY26"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _sections(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    section = ""
    for line in path.read_text(errors="replace").splitlines():
        match = re.match(r"^\s*\[([^]]+)\]", line)
        if match:
            section = match.group(1).upper()
            result.setdefault(section, [])
        elif section:
            result[section].append(line)
    return result


def _series(rows: list[str], series_id: str) -> list[tuple[datetime, float]]:
    values = []
    for line in rows:
        fields = line.split()
        if len(fields) < 4 or fields[0] != series_id:
            continue
        stamp = datetime.strptime(fields[1] + " " + fields[2], "%m/%d/%Y %H:%M")
        values.append((stamp, float(fields[3])))
    return values


def _report_table(lines: list[str], heading: str, header_predicate) -> list[list[str]]:
    heading_index = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if heading_index is None:
        raise ValueError(f"Missing RPT section: {heading}")
    header_index = next(
        (i for i in range(heading_index + 1, len(lines)) if header_predicate(" ".join(lines[i : i + 3]))),
        None,
    )
    if header_index is None:
        raise ValueError(f"Could not locate header for RPT section: {heading}")
    divider_index = next(
        (i for i in range(header_index + 1, len(lines)) if re.match(r"^\s*-{3,}\s*$", lines[i])),
        None,
    )
    if divider_index is None:
        raise ValueError(f"Could not locate table start for RPT section: {heading}")
    records = []
    for line in lines[divider_index + 1 :]:
        if not line.strip() or re.match(r"^\s*-{3,}\s*$", line):
            break
        records.append(line.split())
    return records


def _source_line(relative_path: str, text: str) -> str:
    path = ROOT / relative_path
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if text in line:
            return f"[{relative_path}#L{number}]({relative_path}#L{number})"
    return f"`{relative_path}` (matching line not found)"


def _fmt(value: float | None, digits: int = 3) -> str:
    return "not available" if value is None else f"{value:.{digits}f}"


def main() -> None:
    event = next(row for row in _read_csv(EVENTS_CSV) if row.get("event_id") == "E001")
    event_start = datetime.strptime(event["event_start"], "%Y-%m-%d %H:%M")
    event_end = datetime.strptime(event["event_end"], "%Y-%m-%d %H:%M")

    observations = [row for row in _read_csv(OBSERVATIONS_CSV) if row.get("event_id") == "E001"]
    observation_times = [
        datetime.strptime(row["observation_date"] + " " + row["observation_time_utc"], "%Y-%m-%d %H:%M")
        for row in observations
        if row.get("observation_time_utc")
    ]
    observation_total = sum(float(row["rainfall_mm"]) for row in observations)
    observation_step_hours = sorted({int(row["accumulation_period_hours"]) for row in observations})

    generated_sections = {"TIMESERIES": GENERATED_RAIN.read_text(errors="replace").splitlines()}
    generated = _series(generated_sections["TIMESERIES"], SERIES_ID)
    inp = _sections(BASELINE_INP)
    raingage = next(
        (line.split() for line in inp.get("RAINGAGES", []) if "TIMESERIES" in line.upper()),
        [],
    )
    reference_id = raingage[raingage.index("TIMESERIES") + 1] if "TIMESERIES" in raingage else ""
    embedded = _series(inp.get("TIMESERIES", []), reference_id)
    if not generated or not embedded:
        raise ValueError("Generated or baseline-INP rainfall series is missing")

    time_steps = sorted({(right[0] - left[0]) for left, right in zip(generated, generated[1:])})
    time_step = time_steps[0] if len(time_steps) == 1 else None
    generated_covered_end = generated[-1][0] + time_step if time_step else None
    inp_options = {}
    for line in inp.get("OPTIONS", []):
        fields = line.split()
        if len(fields) >= 2 and not line.lstrip().startswith(";"):
            inp_options[fields[0].upper()] = fields[1:]
    inp_end = datetime.strptime(
        inp_options["END_DATE"][0] + " " + inp_options["END_TIME"][0], "%m/%d/%Y %H:%M:%S"
    )
    series_identical = generated == embedded

    junction_rows = {
        row[0]: row[1:]
        for row in (line.split() for line in inp.get("JUNCTIONS", []))
        if len(row) >= 6 and not row[0].startswith(";")
    }
    allow_ponding = next(
        (fields[1].upper() for line in inp.get("OPTIONS", [])
         if (fields := line.split()) and fields[0].upper() == "ALLOW_PONDING"),
        "not available",
    )
    prepared_junctions = {row["junction_id"]: row for row in _read_csv(JUNCTIONS_CSV)}

    rpt_lines = BASELINE_RPT.read_text(errors="replace").splitlines()
    depth_rows = _report_table(
        rpt_lines,
        "Node Depth Summary",
        lambda text: "Node" in text and "Type" in text and "Meters" in text,
    )
    flood_rows = _report_table(
        rpt_lines,
        "Node Flooding Summary",
        lambda text: "Node" in text and "Flooded" in text and "Meters" in text,
    )
    top_depths = sorted(
        ((row[0], float(row[3])) for row in depth_rows if len(row) > 3 and row[1] == "JUNCTION"),
        key=lambda row: row[1],
        reverse=True,
    )[:10]
    ponding_by_node = {
        row[0]: (float(row[-2]), float(row[-1]))
        for row in flood_rows
        if len(row) >= 2
    }

    output_depths = {}
    with Output(str(BASELINE_OUT)) as output:
        available_nodes = set(output.nodes)
        for node_id, _ in top_depths:
            if node_id not in available_nodes:
                output_depths[node_id] = None
                continue
            samples = output.node_series(node_id, NodeAttribute.INVERT_DEPTH)
            output_depths[node_id] = max(samples.values()) if samples else None

    table = [
        "| Junction ID | Invert THD (m) | RPT max depth (m) | OUT sampled max depth (m) | RPT max ponded depth (m) | Prepared ground THD (m) | Prepared ground MSL (m) | Ponding enabled |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for node_id, max_depth in top_depths:
        prepared = prepared_junctions.get(node_id, {})
        inp_fields = junction_rows.get(node_id, [])
        invert = float(inp_fields[0]) if inp_fields else None
        ponded_depth = ponding_by_node.get(node_id, (0.0, 0.0))[1]
        table.append(
            "| {node} | {invert} | {rpt_depth} | {out_depth} | {ponded} | {ground_thd} | {ground_msl} | {ponding} |".format(
                node=node_id,
                invert=_fmt(invert),
                rpt_depth=_fmt(max_depth),
                out_depth=_fmt(output_depths[node_id]),
                ponded=_fmt(ponded_depth),
                ground_thd=prepared.get("ground_elev_thd_m", "not available"),
                ground_msl=prepared.get("ground_elev_msl_m", "not available"),
                ponding=allow_ponding,
            )
        )

    step_minutes = time_step.total_seconds() / 60 if time_step else None
    metadata_hours = (event_end - event_start).total_seconds() / 3600
    generated_hours = len(generated) * time_step.total_seconds() / 3600 if time_step else None
    inp_duration_hours = (inp_end - datetime.strptime(
        inp_options["START_DATE"][0] + " " + inp_options["START_TIME"][0], "%m/%d/%Y %H:%M:%S"
    )).total_seconds() / 3600
    baseline_sum = sum(value for _, value in generated)
    observations_first = min(observation_times) if observation_times else None
    observations_last = max(observation_times) if observation_times else None
    observations_first_text = observations_first.strftime("%Y-%m-%d %H:%M") if observations_first else "not available"
    observations_last_text = observations_last.strftime("%Y-%m-%d %H:%M") if observations_last else "not available"
    generated_covered_end_text = generated_covered_end.strftime("%Y-%m-%d %H:%M") if generated_covered_end else "unknown"
    observation_period_text = f"{observation_step_hours[0]} h accumulation field" if observation_step_hours else "not available"

    source_refs = {
        "event window": _source_line("scripts/build_rainfall_events.py", '"event_start": "2005-07-26 00:00"'),
        "event rainfall label": _source_line("scripts/build_rainfall_events.py", '"rainfall_24h_mm": 944.2'),
        "first cumulative observation": _source_line("scripts/build_rainfall_observations.py", '("2005-07-26", "03:00", 0.09)'),
        "initial cumulative baseline": _source_line("scripts/build_rainfall_observations.py", "previous_cumulative_mm = 0.0"),
        "interval differencing": _source_line("scripts/build_rainfall_observations.py", "interval_mm = cumulative_mm - previous_cumulative_mm"),
        "24h feature sum": _source_line("scripts/build_rainfall_feature.py", "rainfall_24h = rainfall.sum()"),
        "27h SWMM interval definition": _source_line("scripts/prepare_swmm_datasets.py", 'intervals_3h = ['),
        "15m interval expansion": _source_line("scripts/prepare_swmm_datasets.py", "for start_str, end_str, block_mm in intervals_3h:"),
        "15m series output": _source_line("scripts/prepare_swmm_datasets.py", 'with open(SWMM_OUT_DIR / "timeseries_2005_july26.dat", "w") as f:'),
    }
    elevation_refs = {
        "node invert derivation": _source_line("scripts/prepare_swmm_datasets.py", 'inv = float(min(info["inverts"]))'),
        "DEM ground sample": _source_line("scripts/prepare_swmm_datasets.py", "ground_msl = float(dem_val)"),
        "fallback ground estimate": _source_line("scripts/prepare_swmm_datasets.py", "ground_msl = max(0.5, inv - DATUM_OFFSET + 1.5)"),
        "minimum-depth adjustment": _source_line("scripts/prepare_swmm_datasets.py", "if ground_thd - inv < min_depth:"),
    }

    report = f"""# Ward L Next-Priority Diagnostic

Read-only diagnostic of rainfall duration and the ten largest baseline junction depths. No simulation was run; the existing `models/ward_L_kurla.inp`, `.rpt`, `.out`, and prepared datasets were read as-is.

## Rainfall Duration

| Artifact | Start timestamp | End timestamp / coverage | Records or intervals | Timestep | Total rainfall |
|---|---|---|---:|---:|---:|
| E001 event metadata | {event_start:%Y-%m-%d %H:%M} | {event_end:%Y-%m-%d %H:%M} | elapsed {metadata_hours:g} h | n/a | `rainfall_24h_mm` = {float(event['rainfall_24h_mm']):.1f} mm |
| E001 derived observations | {observations_first_text} | {observations_last_text} | {len(observations)} values ({observation_period_text}) | 3 h values | {observation_total:.2f} mm |
| Generated SWMM time series | {generated[0][0]:%Y-%m-%d %H:%M} | last record {generated[-1][0]:%Y-%m-%d %H:%M}; coverage ends {generated_covered_end_text} | {len(generated)} records / {len(generated)} rainfall intervals ({generated_hours:g} h) | {step_minutes:g} min | {baseline_sum:.3f} mm |
| Baseline INP reference `{reference_id}` | {embedded[0][0]:%Y-%m-%d %H:%M} | last record {embedded[-1][0]:%Y-%m-%d %H:%M}; INP run ends {inp_end:%Y-%m-%d %H:%M} | {len(embedded)} records | {step_minutes:g} min | {sum(value for _, value in embedded):.3f} mm |

The baseline rain gage references `{reference_id}` with a 15-minute `VOLUME` interval. The parsed timestamp/value rows in the embedded series match the generated series: **{series_identical}**. The model run window is {inp_duration_hours:g} h. Event metadata and the generated/embedded SWMM forcing therefore span 27 h, while the same 944.2 mm is labeled as a 24-hour total. The nine source observations are timestamped every 3 h from {observations_first_text} to {observations_last_text}; their first 0.9 mm value is also treated as a 3-hour interval beginning at 26 July 00:00.

**Source location of the duration discrepancy:** {source_refs['first cumulative observation']}, {source_refs['initial cumulative baseline']}, and {source_refs['interval differencing']} create the leading 0.9 mm interval; {source_refs['24h feature sum']} sums all nine 3-hour values into `rainfall_24h`; and {source_refs['27h SWMM interval definition']} / {source_refs['15m interval expansion']} / {source_refs['15m series output']} explicitly generate nine 3-hour blocks (108 15-minute intervals). The event fields are at {source_refs['event window']} and {source_refs['event rainfall label']}. The local artifacts do not establish whether the leading interval should be included in the intended 24-hour rainfall window; no duration/value correction is assumed here.

## Ten Highest Junction Depths

Ranked by maximum depth in the existing baseline RPT. `OUT sampled max` is the largest 15-minute binary-output depth for that node; it can be lower than the RPT maximum because it is sampled at report timesteps.

{chr(10).join(table)}

Invert elevations are from the baseline INP `[JUNCTIONS]` values in THD. Prepared ground elevations are the dataset's `ground_elev_thd_m` / `ground_elev_msl_m`, not verified surveyed rim measurements. The prepared-data producer derives node invert as the minimum incident conduit invert ({elevation_refs['node invert derivation']}); ground elevation is DEM-sampled when valid ({elevation_refs['DEM ground sample']}), otherwise estimated ({elevation_refs['fallback ground estimate']}), then may be raised by a minimum-depth constraint ({elevation_refs['minimum-depth adjustment']}). The prepared CSV does not retain a per-node flag showing which ground-elevation path was used, so that provenance cannot be resolved for each listed node from existing artifacts. Ponding is globally enabled in the baseline (`ALLOW_PONDING {allow_ponding}`).

## Recommendation

Resolve the E001 rainfall window/first 3-hour interval semantics in the source data definition before further model tuning: the forcing artifacts agree with each other, but their 27-hour construction conflicts with the `rainfall_24h_mm` label. This is a sensitivity/input-definition issue, not evidence for choosing which duration is correct.
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Rain series: {len(generated)} x {step_minutes:g} min = {generated_hours:g} h, {baseline_sum:.3f} mm; INP match={series_identical}")
    print(f"Top-depth junctions: {len(top_depths)}; ponding={allow_ponding}")


if __name__ == "__main__":
    main()