"""Read recent Mumbai SYNOP precipitation observations from IMD's public WIS2 feed."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


COLLECTION_URL = (
    "https://wis2box.imd.gov.in/oapi/collections/"
    "urn:wmo:md:in-imd:surface-based-observations.synop/items"
)
STATIONS = {
    "0-20000-0-43003": "Mumbai Santacruz",
    "0-20000-0-43057": "Mumbai Colaba",
}
PRECIPITATION_METRIC = "total_precipitation_or_total_water_equivalent"
CACHE_SECONDS = 600
_cache_lock = threading.Lock()
_cache_expires_at = 0.0
_cache_value: dict[str, Any] | None = None


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _unavailable(error: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "India Meteorological Department (IMD), via WMO WIS 2.0",
        "source_url": COLLECTION_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "rainfall_forecast": "not_connected",
        "stations": [],
        "message": error,
    }


def get_mumbai_observations(force_refresh: bool = False) -> dict[str, Any]:
    """Return cached latest hourly precipitation reports for two Mumbai stations."""
    global _cache_expires_at, _cache_value
    with _cache_lock:
        if not force_refresh and _cache_value is not None and time.monotonic() < _cache_expires_at:
            return _cache_value

        url = (
            f"{COLLECTION_URL}?f=json&limit=1000&sortby=-reportTime"
            "&bbox=72.6,18.8,73.2,19.4"
        )
        request = Request(url, headers={"Accept": "application/geo+json", "User-Agent": "TERRA05/1.0"})
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.load(response)
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            result = _unavailable(f"The IMD observation feed could not be reached: {exc}")
            # Briefly cache failures to avoid repeatedly hitting a down external service.
            _cache_value = result
            _cache_expires_at = time.monotonic() + 60
            return result

        latest: dict[str, tuple[datetime, dict[str, Any]]] = {}
        for feature in payload.get("features", []):
            properties = feature.get("properties") or {}
            station_id = properties.get("wigos_station_identifier")
            if station_id not in STATIONS or properties.get("name") != PRECIPITATION_METRIC:
                continue
            report_time = _utc(properties.get("reportTime"))
            if report_time is None:
                continue
            if station_id not in latest or report_time > latest[station_id][0]:
                latest[station_id] = (report_time, feature)

        now = datetime.now(timezone.utc)
        stations = []
        for station_id, name in STATIONS.items():
            feature = latest.get(station_id, (None, None))[1]
            if feature is None:
                continue
            properties = feature["properties"]
            report_time = _utc(properties.get("reportTime"))
            period_parts = (properties.get("phenomenonTime") or "").split("/")
            period_start = _utc(period_parts[0]) if period_parts else None
            period_end = _utc(period_parts[1]) if len(period_parts) > 1 else report_time
            age_minutes = max(0, int((now - report_time).total_seconds() // 60)) if report_time else None
            raw_value = properties.get("value")
            stations.append({
                "station_id": station_id.rsplit("-", 1)[-1],
                "name": name,
                "latitude": feature["geometry"]["coordinates"][1],
                "longitude": feature["geometry"]["coordinates"][0],
                "rainfall_mm": float(raw_value) if raw_value is not None else None,
                "rainfall_period_start": period_start.isoformat() if period_start else None,
                "rainfall_period_end": period_end.isoformat() if period_end else None,
                "observation_time": report_time.isoformat() if report_time else None,
                "age_minutes": age_minutes,
                "stale": age_minutes is None or age_minutes > 12 * 60,
            })

        if not stations:
            result = _unavailable("No recent Mumbai precipitation reports were present in the IMD feed.")
        else:
            result = {
                "status": "available",
                "source": "India Meteorological Department (IMD), via WMO WIS 2.0",
                "source_url": COLLECTION_URL,
                "fetched_at": now.isoformat(),
                "rainfall_forecast": "not_connected",
                "rainfall_units": "mm over the reported period",
                "stations": stations,
                "message": "Periodic station observations; report age is shown for each station.",
            }
        _cache_value = result
        _cache_expires_at = time.monotonic() + CACHE_SECONDS
        return result
