"""Print a source-backed diagnostic table for saved SWMM Warning 04 entries."""

from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
PILOT_DIR = ROOT / "data" / "swmm_ready" / "pilot_ward_L"


def parse_sections(path):
    sections = {}
    current = None
    for raw_line in path.read_text(errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].upper()
            sections[current] = []
        elif current and line and not line.startswith(";"):
            sections[current].append(line)
    return sections


def main():
    report_text = (MODEL_DIR / "ward_L_kurla.rpt").read_text(errors="replace")
    warning_lines = re.findall(r"^\s*(WARNING\s+04:.*)$", report_text, re.MULTILINE)
    warning_ids = [re.search(r"Conduit\s+(\S+)", line).group(1) for line in warning_lines]
    assert len(warning_ids) == len(set(warning_ids)), "Duplicate Warning 04 links in report"

    conduits = pd.read_csv(
        PILOT_DIR / "swmm_conduits_ward_L.csv",
        dtype={"conduit_id": str, "us_node_id": str, "ds_node_id": str},
    ).set_index("conduit_id")
    junctions = pd.read_csv(
        PILOT_DIR / "swmm_junctions_ward_L.csv", dtype={"junction_id": str}
    ).set_index("junction_id")
    outfalls = pd.read_csv(
        PILOT_DIR / "swmm_outfalls_ward_L.csv", dtype={"outfall_id": str}
    ).set_index("outfall_id")
    node_inverts = pd.concat(
        [junctions["invert_elev_thd_m"], outfalls["invert_elev_thd_m"]]
    ).to_dict()
    nodes = {**junctions.to_dict("index"), **outfalls.to_dict("index")}

    sections = parse_sections(MODEL_DIR / "ward_L_kurla.inp")
    model_nodes = {
        parts[0]: float(parts[1])
        for section in ("JUNCTIONS", "OUTFALLS")
        for line in sections[section]
        for parts in [line.split()]
    }
    model_links = {
        parts[0]: parts
        for line in sections["CONDUITS"]
        for parts in [line.split()]
    }

    print(f"Warning 04 count: {len(warning_ids)}")
    print("Exact report wording: `WARNING 04: minimum elevation drop used for Conduit <ID>`")
    print("| Link | US -> DS | Source inverts U/D (m THD) | Length (m) | Invert slope (m/m) | CSV slope (m/m) | INP slope (m/m) | Ground THD U/D (m) | Source max depth U/D (m) | Classification |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")

    for link_id in warning_ids:
        row = conduits.loc[link_id]
        upstream = str(row["us_node_id"])
        downstream = str(row["ds_node_id"])
        link = model_links[link_id]
        source_slope = (
            float(row["us_invert_thd_m"]) - float(row["ds_invert_thd_m"])
        ) / float(row["length_m"])
        model_up = model_nodes[upstream] + float(link[5])
        model_down = model_nodes[downstream] + float(link[6])
        model_slope = (model_up - model_down) / float(row["length_m"])
        upstream_node = nodes[upstream]
        downstream_node = nodes[downstream]

        assert abs(source_slope) < 1e-12, f"{link_id} is not flat in the source invert fields"
        assert abs(model_slope) < 1e-12, f"{link_id} INP offsets do not preserve its flat inverts"
        assert upstream_node.get("max_depth_m") is not None
        assert downstream_node.get("max_depth_m") is not None

        print(
            f"| {link_id} | {upstream} -> {downstream} "
            f"| {row['us_invert_thd_m']:.3f} / {row['ds_invert_thd_m']:.3f} "
            f"| {row['length_m']:.1f} | {source_slope:.6f} "
            f"| {row['slope_m_per_m']:.4f} | {model_slope:.6f} "
            f"| {upstream_node['ground_elev_thd_m']:.3f} / {downstream_node['ground_elev_thd_m']:.3f} "
            f"| {upstream_node['max_depth_m']:.3f} / {downstream_node['max_depth_m']:.3f} "
            "| Potential geometry/elevation issue (flat) |"
        )

    adverse_ids = {"C_28238", "C_29481"}
    assert adverse_ids.isdisjoint(warning_ids), "A named adverse-slope conduit appears in Warning 04"
    for link_id in sorted(adverse_ids):
        row = conduits.loc[link_id]
        slope = (
            float(row["us_invert_thd_m"]) - float(row["ds_invert_thd_m"])
        ) / float(row["length_m"])
        print(
            f"Adverse but not Warning 04: {link_id}; "
            f"source-derived slope {slope:.6f} m/m; "
            f"CSV slope field {row['slope_m_per_m']:.4f} m/m."
        )


if __name__ == "__main__":
    main()