# Phase 4 Dataset Integrity

- Candidate E001 event-grid rows retained for audit only: 47,758; unique event/grid keys: 47,758.
- Duplicate event/grid keys: 0; conflicting labels per key: 0.
- Event-eligible supervised rows: 0; train/validation/test files are empty by design.
- Supplied target positives: 1,953 of 47,758; label source does not establish a July 2005 match.
- Registry eligibility counts: {'INSUFFICIENT_PROVENANCE': 2, 'INSUFFICIENT_RAINFALL': 2, 'RAIN_ONLY': 1}.
- Canonical candidate dataset SHA-256: `1fc8011111447106c872c47afd1934e6e8ab650610dfe8f731902ffff1c4d076`.

No SWMM output is used as a target. E001 labels remain unverified for this rainfall event; other events have no defensible matching spatial labels. Scenario outputs are for simulation and exploratory ranking, not supervised validation.
