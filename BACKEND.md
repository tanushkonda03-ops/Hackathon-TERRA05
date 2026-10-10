# TERRA05 Backend

Start from the repository root:

```powershell
python -m uvicorn --app-dir . backend.main:app --host 127.0.0.1 --port 8000
```

Set `TERRA05_ROOT` when running from another directory. Optional configuration variables are `TERRA05_MODEL_PATH`, `TERRA05_FEATURES_PATH`, `TERRA05_RISK_GRID_PATH`, `TERRA05_RAINFALL_CATALOG`, `TERRA05_RAINFALL_METADATA`, and `TERRA05_CORS_ORIGINS`.

## Endpoints

- `GET /health` reports API, model artifact, rainfall catalogue, geospatial data, and SWMM readiness.
- `GET /api/v1/system-status` reports the same components independently.
- `GET /api/v1/live-weather` returns the latest periodic Mumbai Santacruz and Colaba precipitation observations from IMD's public WIS 2.0 SYNOP collection, with observation timestamps and age. This endpoint does not provide a forecast or automatically change simulation rainfall inputs.
- `GET /api/v1/scenarios` returns the nine validated rainfall scenarios and their interval records.
- `POST /api/v1/simulation/run` runs a rainfall scenario with optional custom duration/total depth and `tide_level` (`normal`, `high`, or `extreme`). Higher tide reduces effective drainage capacity to represent coastal backwater.
- `POST /api/v1/predict` accepts either `{ "grid_id": 1 }` or WGS84 `{ "latitude": ..., "longitude": ... }`. It returns an uncalibrated historical susceptibility score from the saved scikit-learn pipeline.
- `GET /api/v1/drainage-network` returns existing municipal conduits by default (`?status=all` also includes proposed assets).
- `GET /api/v1/flood-spots` returns the 333 cleaned BMC flood-prone location polygons. These are historical-prone locations, not current inundation observations.
- `GET /api/v1/risk-map?limit=100&offset=0` returns paginated features from the 100 m historical flood-label grid; it is not a live or scenario-specific risk prediction. Bounding-box values use EPSG:32643.

The prediction endpoint is historical spatial susceptibility, not a calibrated probability, event-specific forecast, real-time warning, water-depth prediction, or inundation extent. The repository has no EPA-SWMM `.inp` model, so hydraulic simulation remains unavailable and is reported explicitly by status endpoints.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```
