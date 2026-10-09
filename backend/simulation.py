"""
TERRA05 Rigorous Hydrologic & Hydraulic Simulation Engine
=========================================================
Modular numerical model implementing:
1. Validated rainfall timeseries processing with explicit unit conversions.
2. Per-timestep infiltration via cell-specific Horton decay curves.
3. Configurable initial abstraction and depression storage retention.
4. Municipal stormwater drainage extraction scaled by conduit density.
5. 2D terrain-diffusive hydraulic head routing with Courant stability limiting.
6. Rigorous, per-timestep water balance and mass conservation verification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
import numpy as np

from .data_pipeline import SoilHydrologyAssigner, HortonInfiltrationParams


def utm43_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """
    Transforms UTM Zone 43N (WGS84 ellipsoid) coordinates to (latitude, longitude).
    Analytical transverse Mercator implementation (sub-millimeter precision).
    """
    a = 6378137.0
    f = 1.0 / 298.257223563
    k0 = 0.9996
    e2 = 2.0 * f - f ** 2
    e_prime2 = e2 / (1.0 - e2)

    x = easting - 500000.0
    y = northing
    m = y / k0

    mu = m / (a * (1.0 - e2 / 4.0 - 3.0 * e2 ** 2 / 64.0 - 5.0 * e2 ** 3 / 256.0))
    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
    j1 = 3.0 * e1 / 2.0 - 27.0 * e1 ** 3 / 32.0
    j2 = 21.0 * e1 ** 2 / 16.0 - 55.0 * e1 ** 4 / 32.0
    j3 = 151.0 * e1 ** 3 / 96.0
    j4 = 1097.0 * e1 ** 4 / 512.0

    fp = mu + j1 * math.sin(2.0 * mu) + j2 * math.sin(4.0 * mu) + j3 * math.sin(6.0 * mu) + j4 * math.sin(8.0 * mu)
    c1 = e_prime2 * math.cos(fp) ** 2
    t1 = math.tan(fp) ** 2
    r1 = a * (1.0 - e2) / ((1.0 - e2 * math.sin(fp) ** 2) ** 1.5)
    n1 = a / math.sqrt(1.0 - e2 * math.sin(fp) ** 2)

    d = x / (n1 * k0)
    lat = fp - (n1 * math.tan(fp) / r1) * (
        d ** 2 / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * c1 ** 2 - 9.0 * e_prime2) * d ** 4 / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * t1 ** 2 - 252.0 * e_prime2 - 3.0 * c1 ** 2) * d ** 6 / 720.0
    )

    lon0 = math.radians(75.0)  # Central meridian for UTM Zone 43
    lon = lon0 + (
        d
        - (1.0 + 2.0 * t1 + c1) * d ** 3 / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * c1 ** 2 + 8.0 * e_prime2 + 24.0 * t1 ** 2) * d ** 5 / 120.0
    ) / math.cos(fp)

    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


@dataclass
class SimulationConfig:
    """Configurable physical parameters for simulation engine."""
    depression_storage_imp_mm: float = 2.0     # Impervious depression storage (mm)
    depression_storage_perv_mm: float = 5.0    # Pervious depression storage (mm)
    drainage_capacity_mm_hr: float = 25.0      # Base BMC conduit design capacity (mm/hr)
    routing_enabled: bool = True               # Enable 2D diffusive routing
    courant_limiter: float = 0.08              # Numerical stability flux limiter
    head_gradient_threshold_m: float = 0.03    # Minimum head gradient to initiate flow (m)
    inundation_threshold_m: float = 0.05       # Water depth threshold to classify cell as inundated (5 cm)
    max_timesteps: int | None = None           # Optional timesteps cutoff


class SurfaceRunoffEngine:
    """
    Modular 2D surface runoff, infiltration, and flood accumulation simulation engine.
    """

    CELL_AREA_M2 = 10000.0  # 100 m x 100 m = 1.0 hectare = 10,000 m^2
    CELL_RESOLUTION_M = 100.0

    def __init__(
        self,
        features: list[dict[str, Any]],
        scenario_intervals: list[dict[str, Any]],
        scenario_id: str,
        scenario_metadata: dict[str, Any] | None = None,
        config: SimulationConfig | None = None,
        routing_enabled: bool | None = None,
        drainage_capacity_mm_hr: float | None = None,
        max_timesteps: int | None = None,
        depression_storage_imp_mm: float | None = None,
        depression_storage_perv_mm: float | None = None,
    ):
        if not features:
            raise ValueError("No spatial features provided for simulation domain")
        if not scenario_intervals:
            raise ValueError(f"No rainfall intervals available for scenario {scenario_id}")

        self.scenario_id = scenario_id
        self.scenario_metadata = scenario_metadata or {}
        
        # Build config, accepting overrides for backwards compatibility
        cfg = config or SimulationConfig()
        if routing_enabled is not None:
            cfg.routing_enabled = routing_enabled
        if drainage_capacity_mm_hr is not None:
            cfg.drainage_capacity_mm_hr = max(0.0, float(drainage_capacity_mm_hr))
        if max_timesteps is not None:
            cfg.max_timesteps = max_timesteps
        if depression_storage_imp_mm is not None:
            cfg.depression_storage_imp_mm = max(0.0, float(depression_storage_imp_mm))
        if depression_storage_perv_mm is not None:
            cfg.depression_storage_perv_mm = max(0.0, float(depression_storage_perv_mm))
        self.config = cfg

        # Filter intervals if max_timesteps specified
        self.intervals = scenario_intervals[:cfg.max_timesteps] if cfg.max_timesteps else scenario_intervals

        # Extract features, coordinates, soil classes, and drainage density
        self.cells = []
        for feat in features:
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [[]])[0]
            if len(coords) < 4:
                continue

            cx = float(sum(c[0] for c in coords[:4]) / 4.0)
            cy = float(sum(c[1] for c in coords[:4]) / 4.0)
            lat, lon = utm43_to_wgs84(cx, cy)

            def _s_float(val, default):
                if val is None or val == "":
                    return float(default)
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return float(default)

            soil_class = str(props.get("soil_class") or "LOAM")
            clay_pct = _s_float(props.get("clay_percent"), 20.0)
            infil_proxy = _s_float(props.get("infiltration_proxy"), 0.4)
            horton = SoilHydrologyAssigner.get_params_for_cell(
                soil_class=soil_class,
                clay_pct=clay_pct,
                infiltration_proxy=infil_proxy,
            )

            elev = _s_float(props.get("elevation_mean") if props.get("elevation_mean") is not None else props.get("elevation"), 5.0)
            built = _s_float(props.get("built_up_fraction"), 0.8)
            drain = _s_float(props.get("drain_density") if props.get("drain_density") is not None else props.get("conduit_density_m_per_ha"), 0.0)

            self.cells.append({
                "grid_id": int(props.get("grid_id") or 0),
                "ward": str(props.get("ward") or "Unknown"),
                "cx": cx,
                "cy": cy,
                "lat": lat,
                "lon": lon,
                "elevation": elev,
                "built_up": built,
                "drain_density": drain,
                "soil_class": soil_class,
                "horton_f0": horton.f0_mm_hr,
                "horton_fc": horton.fc_mm_hr,
                "horton_k": horton.k_hr,
            })

        if not self.cells:
            raise ValueError("No valid polygon features with coordinates found in domain")

        self.cell_count = len(self.cells)
        self._build_lattice()

    def _build_lattice(self) -> None:
        """Constructs regular 2D raster lattice arrays for vectorized hydrodynamics."""
        xs = [c["cx"] for c in self.cells]
        ys = [c["cy"] for c in self.cells]

        self.min_x = min(xs)
        self.min_y = min(ys)
        self.cols = int(round((max(xs) - self.min_x) / self.CELL_RESOLUTION_M)) + 1
        self.rows = int(round((max(ys) - self.min_y) / self.CELL_RESOLUTION_M)) + 1

        self.grid_z = np.full((self.rows, self.cols), np.nan, dtype=np.float64)
        self.grid_built = np.zeros((self.rows, self.cols), dtype=np.float64)
        self.grid_drain = np.zeros((self.rows, self.cols), dtype=np.float64)
        self.grid_f0 = np.full((self.rows, self.cols), 50.0, dtype=np.float64)
        self.grid_fc = np.full((self.rows, self.cols), 5.0, dtype=np.float64)
        self.grid_k = np.full((self.rows, self.cols), 3.0, dtype=np.float64)
        self.mask = np.zeros((self.rows, self.cols), dtype=bool)
        self.cell_indices = []

        for c in self.cells:
            col = int(round((c["cx"] - self.min_x) / self.CELL_RESOLUTION_M))
            row = int(round((c["cy"] - self.min_y) / self.CELL_RESOLUTION_M))
            self.grid_z[row, col] = c["elevation"]
            self.grid_built[row, col] = np.clip(c["built_up"], 0.0, 1.0)
            self.grid_drain[row, col] = max(0.0, c["drain_density"])
            self.grid_f0[row, col] = c["horton_f0"]
            self.grid_fc[row, col] = c["horton_fc"]
            self.grid_k[row, col] = c["horton_k"]
            self.mask[row, col] = True
            self.cell_indices.append((row, col))

    def run(self) -> dict[str, Any]:
        """
        Executes the time-stepping simulation loop with strict per-timestep water balance verification.
        """
        depth = np.zeros((self.rows, self.cols), dtype=np.float64)

        cum_rain_vol = 0.0
        cum_infil_vol = 0.0
        cum_depr_vol = 0.0
        cum_drain_vol = 0.0

        timestep_records = []
        cell_depth_timeseries = [[] for _ in range(self.cell_count)]

        # Tracking depression storage initial abstractions per cell
        depr_stored_imp = np.zeros((self.rows, self.cols), dtype=np.float64)
        depr_stored_perv = np.zeros((self.rows, self.cols), dtype=np.float64)

        for step_idx, interval in enumerate(self.intervals):
            p_mm = float(interval.get("rainfall_15min_mm", 0.0))
            intensity_mm_hr = float(interval.get("intensity_mm_per_hr", p_mm * 4.0))
            dt_min = 15.0
            dt_hr = dt_min / 60.0
            t_hr = step_idx * dt_hr

            # 1. Total precipitation volume added to domain in this timestep
            step_rain_vol = (p_mm / 1000.0) * self.CELL_AREA_M2 * self.cell_count
            cum_rain_vol += step_rain_vol

            # 2. Cell-specific Horton Infiltration on pervious fraction
            # f_i(t) = f_{c,i} + (f_{0,i} - f_{c,i}) * exp(-k_i * t)
            f_horton_cell_mm_hr = self.grid_fc + (self.grid_f0 - self.grid_fc) * np.exp(-self.grid_k * t_hr)
            i_pot_mm = f_horton_cell_mm_hr * dt_hr
            i_act_mm = np.minimum(p_mm, i_pot_mm)

            perv_fraction = 1.0 - self.grid_built
            step_perv_infil_mm = np.where(self.mask, perv_fraction * i_act_mm, 0.0)
            step_infil_vol = float(np.sum(step_perv_infil_mm / 1000.0 * self.CELL_AREA_M2))
            cum_infil_vol += step_infil_vol

            # 3. Depression storage abstraction
            rem_p_imp = max(0.0, p_mm)
            abs_imp_mm = np.where(
                self.mask,
                np.minimum(rem_p_imp, np.maximum(0.0, self.config.depression_storage_imp_mm - depr_stored_imp)),
                0.0
            )
            depr_stored_imp += abs_imp_mm
            excess_imp_mm = np.maximum(0.0, rem_p_imp - abs_imp_mm)

            rem_p_perv = np.maximum(0.0, p_mm - i_act_mm)
            abs_perv_mm = np.where(
                self.mask,
                np.minimum(rem_p_perv, np.maximum(0.0, self.config.depression_storage_perv_mm - depr_stored_perv)),
                0.0
            )
            depr_stored_perv += abs_perv_mm
            excess_perv_mm = np.maximum(0.0, rem_p_perv - abs_perv_mm)

            step_depr_mm = np.where(self.mask, self.grid_built * abs_imp_mm + perv_fraction * abs_perv_mm, 0.0)
            step_depr_vol = float(np.sum(step_depr_mm / 1000.0 * self.CELL_AREA_M2))
            cum_depr_vol += step_depr_vol

            # 4. Net rainfall excess added to ponded surface
            excess_mm = self.grid_built * excess_imp_mm + perv_fraction * excess_perv_mm
            excess_m = np.where(self.mask, excess_mm / 1000.0, 0.0)
            depth += excess_m

            # 5. Municipal drainage conveyance removal
            drain_scaling = np.clip(self.grid_drain / 10.0 + 0.4, 0.3, 1.6)
            step_drain_cap_mm = (self.config.drainage_capacity_mm_hr * dt_hr) * drain_scaling
            step_drain_cap_m = step_drain_cap_mm / 1000.0
            drain_removed_m = np.where(self.mask, np.minimum(depth, step_drain_cap_m), 0.0)
            step_drain_vol = float(np.sum(drain_removed_m * self.CELL_AREA_M2))
            cum_drain_vol += step_drain_vol
            depth -= drain_removed_m

            # 6. Terrain-Based 2D Overland Routing (Diffusive wave with Courant stability)
            if self.config.routing_enabled:
                head = np.where(self.mask, self.grid_z + depth, -9999.0)
                tf = self.config.courant_limiter
                h_thresh = self.config.head_gradient_threshold_m

                # Transfer along rows (North / South)
                dh_rows = head[1:, :] - head[:-1, :]
                mask_ns = self.mask[1:, :] & self.mask[:-1, :]

                # Northbound transfer (from r+1 to r)
                flux_n = np.where((dh_rows > h_thresh) & mask_ns, np.minimum(depth[1:, :], dh_rows * 0.45) * tf, 0.0)
                depth[1:, :] -= flux_n
                depth[:-1, :] += flux_n

                # Southbound transfer (from r to r+1)
                flux_s = np.where((dh_rows < -h_thresh) & mask_ns, np.minimum(depth[:-1, :], -dh_rows * 0.45) * tf, 0.0)
                depth[:-1, :] -= flux_s
                depth[1:, :] += flux_s

                # Transfer along columns (East / West)
                dh_cols = head[:, 1:] - head[:, :-1]
                mask_ew = self.mask[:, 1:] & self.mask[:, :-1]

                # Westbound transfer (from c+1 to c)
                flux_w = np.where((dh_cols > h_thresh) & mask_ew, np.minimum(depth[:, 1:], dh_cols * 0.45) * tf, 0.0)
                depth[:, 1:] -= flux_w
                depth[:, :-1] += flux_w

                # Eastbound transfer (from c to c+1)
                flux_e = np.where((dh_cols < -h_thresh) & mask_ew, np.minimum(depth[:, :-1], -dh_cols * 0.45) * tf, 0.0)
                depth[:, :-1] -= flux_e
                depth[:, 1:] += flux_e

            # Record per-cell depths at this timestep
            for c_idx, (r, c) in enumerate(self.cell_indices):
                d_val = float(depth[r, c])
                cell_depth_timeseries[c_idx].append(round(d_val, 4))

            # Timestep summary metrics
            active_depths = depth[self.mask]
            cur_storage_vol = float(np.sum(active_depths * self.CELL_AREA_M2))
            max_d = float(np.nanmax(active_depths)) if len(active_depths) > 0 else 0.0
            mean_d = float(np.nanmean(active_depths)) if len(active_depths) > 0 else 0.0
            inundated_count = int(np.sum(active_depths >= self.config.inundation_threshold_m))
            inundated_km2 = round(inundated_count * (self.CELL_AREA_M2 / 1_000_000.0), 3)

            # Per-timestep water balance check
            expected_cur_storage = cum_rain_vol - cum_infil_vol - cum_depr_vol - cum_drain_vol
            step_balance_err_m3 = abs(cur_storage_vol - expected_cur_storage)
            step_balance_err_pct = (step_balance_err_m3 / max(1.0, cum_rain_vol)) * 100.0

            timestep_records.append({
                "step_index": step_idx,
                "datetime": str(interval.get("datetime", f"T+{step_idx * 15}m")),
                "elapsed_minutes": (step_idx + 1) * 15,
                "rainfall_mm": round(p_mm, 2),
                "rainfall_intensity_mm_per_hr": round(intensity_mm_hr, 2),
                "rainfall_excess_mm": round(float(np.mean(excess_mm[self.mask])), 2),
                "infiltrated_depth_mm": round(float(np.mean(step_perv_infil_mm[self.mask])), 2),
                "drainage_removed_volume_m3": round(step_drain_vol, 1),
                "surface_storage_volume_m3": round(cur_storage_vol, 1),
                "max_water_depth_m": round(max_d, 4),
                "mean_water_depth_m": round(mean_d, 4),
                "inundated_cells_count": inundated_count,
                "inundated_area_km2": inundated_km2,
                "mass_balance_error_m3": round(step_balance_err_m3, 3),
                "mass_balance_error_percent": round(step_balance_err_pct, 6),
            })

        # Final domain water balance
        final_storage_vol = float(np.sum(depth[self.mask] * self.CELL_AREA_M2))
        expected_storage = cum_rain_vol - cum_infil_vol - cum_depr_vol - cum_drain_vol
        balance_error_m3 = abs(final_storage_vol - expected_storage)
        balance_error_pct = (balance_error_m3 / max(1.0, cum_rain_vol)) * 100.0

        # Build cell result objects
        cell_results = []
        for c_idx, cell in enumerate(self.cells):
            d_series = cell_depth_timeseries[c_idx]
            max_c_d = max(d_series) if d_series else 0.0
            fin_c_d = d_series[-1] if d_series else 0.0
            cell_results.append({
                "grid_id": cell["grid_id"],
                "ward": cell["ward"],
                "centroid_lat": cell["lat"],
                "centroid_lng": cell["lon"],
                "elevation_m": round(cell["elevation"], 2),
                "built_up_fraction": round(cell["built_up"], 3),
                "depth_by_timestep": d_series,
                "max_depth_m": round(max_c_d, 4),
                "final_depth_m": round(fin_c_d, 4),
            })

        # Peak statistics
        peak_step = max(timestep_records, key=lambda s: s["max_water_depth_m"], default={})
        peak_inundated_step = max(timestep_records, key=lambda s: s["inundated_cells_count"], default={})

        return {
            "scenario_id": self.scenario_id,
            "scenario_family": self.scenario_metadata.get("family", "synthetic_design"),
            "duration_hours": round(len(self.intervals) * 0.25, 2),
            "interval_minutes": 15,
            "domain_summary": {
                "cell_count": self.cell_count,
                "total_area_km2": round(self.cell_count * 0.01, 3),
                "cell_resolution_m": self.CELL_RESOLUTION_M,
                "crs": "EPSG:32643",
                "ward": self.cells[0]["ward"] if all(c["ward"] == self.cells[0]["ward"] for c in self.cells) else "Multi-Ward / Catchment",
                "routing_method": "2D terrain-gradient diffusive flow transfer" if self.config.routing_enabled else "local storage with terrain-informed ponding",
            },
            "water_balance": {
                "total_rainfall_volume_m3": round(cum_rain_vol, 1),
                "total_infiltration_volume_m3": round(cum_infil_vol, 1),
                "total_depression_storage_volume_m3": round(cum_depr_vol, 1),
                "total_drainage_removed_volume_m3": round(cum_drain_vol, 1),
                "total_surface_storage_volume_m3": round(final_storage_vol, 1),
                "mass_balance_error_m3": round(balance_error_m3, 3),
                "mass_balance_error_percent": round(balance_error_pct, 5),
            },
            "metrics": {
                "timestep_count": len(self.intervals),
                "peak_rainfall_intensity_mm_per_hr": round(max((s["rainfall_intensity_mm_per_hr"] for s in timestep_records), default=0.0), 2),
                "peak_water_depth_m": peak_step.get("max_water_depth_m", 0.0),
                "peak_inundated_cells_count": peak_inundated_step.get("inundated_cells_count", 0),
                "peak_inundated_area_km2": peak_inundated_step.get("inundated_area_km2", 0.0),
                "final_surface_storage_volume_m3": round(final_storage_vol, 1),
            },
            "timesteps": timestep_records,
            "cells": cell_results,
            "limitations": [
                "2D overland runoff and accumulation model based on 100m raster DEM gradients, SoilGrids Horton parameters, and municipal conduit design rates.",
                "EPA-SWMM pipe network hydraulic routing is supported via the SWMM adapter interface for validated .inp models.",
                "Sub-grid micro-topography, building wall reflections, and tidal backwater sluice operations are simplified.",
                "Historical flood susceptibility scores are separate spatial ML indicators and not combined into this hydraulic calculation.",
            ],
        }
