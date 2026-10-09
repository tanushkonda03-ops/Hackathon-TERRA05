# Scenario API Contract

## `POST /api/v1/scenario/run`

Manual request: `{"mode":"custom","total_rainfall_mm":150,"duration_minutes":360}`. Time-series request: `{"mode":"custom","profile_mm":[0,5,13.75]}`; values are 15-minute rainfall depths in mm. Historical replay: `{"mode":"historical_replay","event_id":"E001"}`. Returns HTTP 202 and a job containing `simulation_id`, `scenario_id`, source/hash, status and timestamps. Inputs reject mismatched mode fields, non-finite/negative rainfall, unsupported events, over 27-hour profiles, and non-15-minute manual durations.

## `GET /api/v1/scenario/{id}`

Returns job status, progress, cache state, SWMM summary, failure detail and result path. A scenario can be `QUEUED`, `RUNNING`, `PHYSICS_COMPLETE`, `ML_RUNNING`, `COMPLETE`, `FAILED_PHYSICS`, or `FAILED_ML`.

## `GET /api/v1/scenario/{id}/results`

Returns citywide `risk_map` rows, the highest ranked critical-asset cells, score semantics, physics coverage/fallback counts, decision support and measured performance. Returns 409 until complete and 404 for an unknown id.

Existing `/api/v1/ml/predict` and `/api/v1/simulation/swmm` endpoints are retained. Scenario risk scores are uncalibrated extrapolations and are not official warning probabilities or measured flood depths.
