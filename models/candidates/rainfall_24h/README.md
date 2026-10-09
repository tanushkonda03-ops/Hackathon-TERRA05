# Ward L Corrected 24-hour Rainfall Candidate

Reproduce the metadata/features update, labelled rainfall series, isolated candidate INP, SWMM run, and baseline comparison from the repository root:

```powershell
python scripts/run_rainfall_24h_candidate.py
```

The script reads the existing nine-row E001 observation table without rewriting it. Per the controlled correction, it excludes the first 0.9 mm block and uses the remaining eight 3-hour increments (03:00 26 July to 03:00 27 July 2005), whose arithmetic sum is 943.3 mm. It retains the existing 944.2 mm/27-hour series as a separately named diagnostic. This selection is not independent verification of the official historical rainfall total; local files do not establish the physical cumulative-reading semantics of the first record.

The candidate INP changes only the rainfall series/reference and rainfall/run reporting start times needed for the 24-hour window. Its RPT, OUT, run log, and baseline comparison CSV are stored here. The original Ward L INP/RPT/OUT and the existing sensitivity experiment directories are preserved. This is a controlled input-duration correction, not calibration or validation.