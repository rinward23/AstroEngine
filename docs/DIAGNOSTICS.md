# >>> AUTO-GEN BEGIN: Diagnostics Guide v1.0
# AstroEngine Diagnostics ("doctor")

Quickly verify your environment, imports, ephemeris path, and runtime health.

## Run
```bash
# human-readable report
python -m astroengine.diagnostics

# JSON for machines/CI
python -m astroengine.diagnostics --json

# Fail on WARN (treat as errors)
python -m astroengine.diagnostics --strict

# Optional: Swiss Ephemeris smoketest (Sun..Saturn at now)
python -m astroengine.diagnostics --smoketest
# or explicit instant:
python -m astroengine.diagnostics --smoketest "2025-01-01T00:00:00Z"
```

## Exit codes

* `0`: no FAIL (and no WARN if `--strict`)
* `1`: at least one FAIL (or WARN with `--strict`)

## Notes

* If `pyswisseph` is missing, status is `WARN`. Install it and set `SE_EPHE_PATH` to high-precision data for best results.
* Diagnostics never require network access and will not modify your system.
* The report now surfaces the active ephemeris time-scale (`UTC→TT` by default) and whether the observer is geocentric or topocentric.

## API & UI integrations

* `GET /v1/doctor` returns Swiss ephemeris probes, database connectivity, migration status, cache metrics, settings ranges, and disk usage as JSON for operators and monitoring agents.
* The "🩺 System Doctor" Streamlit page (under `ui/streamlit/pages/13_System_Doctor.py`) delegates rendering to `ui/streamlit/doctor.py` for consistent visuals and remediation guidance.

# >>> AUTO-GEN END: Diagnostics Guide v1.0
