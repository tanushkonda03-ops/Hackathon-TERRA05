# TERRA05 Backend

Run from the repository root:

```powershell
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The fitted artifact must exist at `models/artifacts/static_flood_susceptibility_lr_v1.joblib`; recreate it with `.venv/Scripts/python.exe scripts/train_static_flood_susceptibility.py`. The existing Vite client uses `http://127.0.0.1:8000`; CORS permits localhost/127.0.0.1 on ports 5173 and 4173.

Implemented routes: `GET /health`, `GET /api/v1/system-status`, `GET /api/v1/scenarios`, `GET /api/v1/risk-map`, `POST /api/v1/predict`, and `GET /api/v1/drainage-network`. `POST /api/v1/simulation/run` returns HTTP 501: the classifier does not simulate rainfall, tides, water depth, or SWMM hydraulics.

Prediction accepts either `{ "grid_id": 1201 }` or `{ "latitude": 19.05, "longitude": 72.86 }`. The response contains `susceptibility_score`, `predicted_class`, `decision_threshold`, model version, score semantics, and limitations. The score is not a calibrated probability.