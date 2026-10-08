"""
Download additional Mumbai flood-model data.

Confirmed BMC ArcGIS REST layer IDs:
- Wards: 238
- Landuse: 281
- Railway Lines: 284
- Building: 283
- Hydro Line: 286
- Road Centerline: 156
- Bridges: 450
- Fire Stations: 213
- Hospitals: 214
- Police Stations: 221
- Temporary Shelters: 232
- Vulnerable Settlements: 346
- Flow Level Sensor: 345
- Mumbai Contour: 217
- Disaster Management Wards: 237

BMC supports GeoJSON queries and uses  EPSG:32643 for these layers.
"""

from pathlib import Path
import json, time, requests

BASE = "https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/MCGMGIS_Departments_Master_All_Layers/MapServer"

ROOT = Path("data")
RAW_BMC = ROOT / "raw" / "bmc"
RAW_BMC.mkdir(parents=True, exist_ok=True)
RAW_EXT = ROOT / "raw" / "external"
RAW_EXT.mkdir(parents=True, exist_ok=True)

BMC_LAYERS = {
    "wards": 238,
    "landuse": 281,
    "railways": 284,
    "buildings": 283,
    "hydro_lines": 286,
    "roads": 156,
    "bridges": 450,
    "fire_stations": 213,
    "hospitals": 214,
    "police_stations": 221,
    "temporary_shelters": 232,
    "vulnerable_settlements": 346,
    "flow_level_sensors": 345,
    "mumbai_contour": 217,
    "disaster_wards": 237,
}

def download_arcgis_layer(name, layer_id, page_size=1000):
    out = RAW_BMC / f"{name}.geojson"
    if out.exists() and out.stat().st_size > 100:
        print(f"[SKIP] {out}")
        return

    url = f"{BASE}/{layer_id}/query"
    features = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultRecordCount": page_size,
            "resultOffset": offset,
        }

        r = requests.get(url, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()

        batch = data.get("features", [])
        if not batch:
            break

        features.extend(batch)
        print(f"{name}: {len(features)} features")

        if len(batch) < page_size:
            break

        offset += page_size
        time.sleep(0.1)

    result = {
        "type": "FeatureCollection",
        "name": name,
        "features": features,
    }

    out.write_text(json.dumps(result), encoding="utf-8")
    print(f"[SAVED] {out} ({len(features)} features)")

for name, layer_id in BMC_LAYERS.items():
    download_arcgis_layer(name, layer_id)

print("\nBMC download complete.")
