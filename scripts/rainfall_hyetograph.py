"""Small shared helper for the local July 2005 SWMM hyetographs."""

from __future__ import annotations

from datetime import datetime, timedelta


WEIGHTS = tuple(value / 1.0 for value in (0.02, 0.04, 0.06, 0.09, 0.13, 0.16, 0.16, 0.13, 0.09, 0.06, 0.04, 0.02))


def disaggregate_3h_intervals(
    intervals: list[tuple[datetime, datetime, float]], *, conserve_block_totals: bool = False
) -> list[tuple[datetime, float]]:
    records = []
    for start, end, total_mm in intervals:
        if end - start != timedelta(hours=3):
            raise ValueError(f"Expected a 3-hour rainfall interval, got {start} to {end}")
        values = [round(total_mm * weight, 3) for weight in WEIGHTS]
        if conserve_block_totals:
            values[5] = round(values[5] + total_mm - sum(values), 3)
        for index, value in enumerate(values):
            records.append((start + timedelta(minutes=15 * index), value))
    return records


def render_swmm_series(series_id: str, records: list[tuple[datetime, float]], title: str) -> str:
    lines = [f";{title}", ";Date       Time     Rainfall_mm"]
    for timestamp, rainfall_mm in records:
        value = str(round(float(rainfall_mm), 3))
        lines.append(
            f"{series_id} {timestamp:%m/%d/%Y} {timestamp:%H:%M} {value}"
        )
    return "\n".join(lines) + "\n"