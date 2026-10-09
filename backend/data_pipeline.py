"""
TERRA05 Geospatial & Hydrologic Data Pipeline
=============================================
Reusable utilities for:
1. Soil-informed infiltration parameter assignment (Horton & Green-Ampt models).
2. D8 topographic flow direction and hydraulic head gradient routing.
3. Grid alignment, catchment bounding box extraction, and coordinate transformation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass(frozen=True)
class HortonInfiltrationParams:
    """Horton infiltration model parameters with explicit units."""
    f0_mm_hr: float       # Initial infiltration capacity (mm/hr)
    fc_mm_hr: float       # Minimum / saturated infiltration capacity (mm/hr)
    k_hr: float           # Infiltration decay rate coefficient (hr^-1)
    dry_time_days: float  # Drying time to recover initial capacity (days)


class SoilHydrologyAssigner:
    """
    Translates soil classification and texture fractions (sand, silt, clay)
    into physically sound, standard hydrologic infiltration parameters.
    Based on USDA Natural Resources Conservation Service (NRCS) and ASCE standards.
    """

    DEFAULT_PARAMS = {
        "SAND": HortonInfiltrationParams(f0_mm_hr=120.0, fc_mm_hr=25.0, k_hr=2.0, dry_time_days=3.0),
        "SANDY_LOAM": HortonInfiltrationParams(f0_mm_hr=75.0, fc_mm_hr=12.0, k_hr=2.5, dry_time_days=4.0),
        "LOAM": HortonInfiltrationParams(f0_mm_hr=50.0, fc_mm_hr=5.0, k_hr=3.0, dry_time_days=7.0),
        "SILT_LOAM": HortonInfiltrationParams(f0_mm_hr=45.0, fc_mm_hr=4.0, k_hr=3.0, dry_time_days=7.0),
        "CLAY_LOAM": HortonInfiltrationParams(f0_mm_hr=30.0, fc_mm_hr=2.5, k_hr=3.5, dry_time_days=8.0),
        "CLAY": HortonInfiltrationParams(f0_mm_hr=15.0, fc_mm_hr=1.2, k_hr=4.0, dry_time_days=10.0),
    }

    @classmethod
    def get_params_for_cell(
        cls,
        soil_class: str | None,
        clay_pct: float | None = None,
        sand_pct: float | None = None,
        infiltration_proxy: float | None = None,
    ) -> HortonInfiltrationParams:
        norm_class = str(soil_class or "LOAM").strip().upper().replace(" ", "_")
        base = cls.DEFAULT_PARAMS.get(norm_class, cls.DEFAULT_PARAMS["LOAM"])

        # Fine-tune based on clay content if available
        if clay_pct is not None and not math.isnan(clay_pct) and clay_pct > 0:
            clay_factor = np.clip(1.0 - (clay_pct - 20.0) / 60.0, 0.4, 1.4)
            f0 = base.f0_mm_hr * clay_factor
            fc = base.fc_mm_hr * clay_factor
            return HortonInfiltrationParams(
                f0_mm_hr=round(float(f0), 2),
                fc_mm_hr=round(float(fc), 2),
                k_hr=base.k_hr,
                dry_time_days=base.dry_time_days,
            )

        # Fine-tune based on infiltration proxy (0.0 to 1.0) if provided
        if infiltration_proxy is not None and not math.isnan(infiltration_proxy) and infiltration_proxy > 0:
            scale = np.clip(infiltration_proxy / 0.4, 0.6, 1.4)
            return HortonInfiltrationParams(
                f0_mm_hr=round(float(base.f0_mm_hr * scale), 2),
                fc_mm_hr=round(float(base.fc_mm_hr * scale), 2),
                k_hr=base.k_hr,
                dry_time_days=base.dry_time_days,
            )

        return base


class D8FlowRouter:
    """
    Computes D8 single-direction flow paths and steepest downward slopes
    across a digital elevation raster.
    """

    # D8 Direction codes: 1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE (ArcGIS/USGS standard)
    DIRECTIONS = [
        (0, 1, 1, 100.0),            # East
        (1, 1, 2, 141.421356),       # South-East
        (1, 0, 4, 100.0),            # South
        (1, -1, 8, 141.421356),      # South-West
        (0, -1, 16, 100.0),          # West
        (-1, -1, 32, 141.421356),    # North-West
        (-1, 0, 64, 100.0),          # North
        (-1, 1, 128, 141.421356),    # North-East
    ]

    @classmethod
    def compute_d8_directions(
        cls,
        dem: np.ndarray,
        cell_size_m: float = 100.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Computes the D8 flow direction code and steepest slope for each grid cell.
        Returns:
            flow_dir: 2D array of D8 direction codes (0 for pit / flat).
            steepest_slope: 2D array of steepest downward slope (m/m).
        """
        rows, cols = dem.shape
        flow_dir = np.zeros((rows, cols), dtype=np.int32)
        steepest_slope = np.zeros((rows, cols), dtype=np.float64)

        for dr, dc, code, dist_scale in cls.DIRECTIONS:
            # Shift neighbor elevations
            r_start = max(0, dr)
            r_end = rows + min(0, dr)
            c_start = max(0, dc)
            c_end = cols + min(0, dc)

            dist_m = dist_scale * (cell_size_m / 100.0)

            src_r_start = max(0, -dr)
            src_r_end = rows - max(0, dr)
            src_c_start = max(0, -dc)
            src_c_end = cols - max(0, dc)

            neighbor_z = dem[src_r_start:src_r_end, src_c_start:src_c_end]
            current_z = dem[r_start:r_end, c_start:c_end]

            drop = current_z - neighbor_z
            slope = drop / dist_m

            better_slope = slope > steepest_slope[r_start:r_end, c_start:c_end]
            steepest_slope[r_start:r_end, c_start:c_end] = np.where(better_slope, slope, steepest_slope[r_start:r_end, c_start:c_end])
            flow_dir[r_start:r_end, c_start:c_end] = np.where(better_slope, code, flow_dir[r_start:r_end, c_start:c_end])

        return flow_dir, steepest_slope
