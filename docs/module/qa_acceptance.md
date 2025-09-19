# QA & Acceptance Specification

- **Module**: `qa_acceptance`
- **Author**: AstroEngine Quality Guild
- **Date**: 2024-05-27
- **Source datasets**: Golden JSONL scenarios (`tests/data/golden_events.jsonl`), Solar Fire comparison exports (`exports/qa/*.csv`), Swiss Ephemeris ephemeris cache checksums, AstroEngine performance logs (`observability/perf_samples.parquet`).
- **Downstream links**: property tests (`tests/property/test_transit_symmetry.py`), performance benchmarks (`docs/PERFORMANCE_BENCH_PLAN.md`), interop docs (`docs/module/interop.md`).

This document defines the QA controls required before marking the specification complete. All acceptance metrics rely on real Solar Fire comparisons or recorded performance data; synthetic scenarios are prohibited.

## Determinism Controls

1. **Golden dataset**: `tests/data/golden_events.jsonl` stores canonical event payloads with Solar Fire URNs. Every change requires recomputing checksums recorded in `tests/data/golden_events.jsonl.sha256`.
2. **Lockstep ephemeris**: QA runs `python -m astroengine.infrastructure.environment numpy pandas scipy` to confirm package versions before executing tests.
3. **Randomness ban**: Lint failing when encountering non-deterministic constructs. Acceptable randomness must use seeded pseudo-RNG with seeds stored in the golden dataset header.
4. **Time zone freeze**: All QA commands set `TZ=UTC` to avoid DST-induced drift; enforcement via pytest fixture `tests/conftest.py::force_utc`.

## Property Testing Inventory

| Property | Test file | Description | Data source |
| -------- | --------- | ----------- | ----------- |
| Angular wrapping | `tests/property/test_transit_symmetry.py::test_longitude_wrapping` | Ensures Δλ remains continuous across 0°/360° | Solar Fire aspect series |
| Severity symmetry | `tests/property/test_transit_symmetry.py::test_severity_symmetry` | Applying vs separating produce mirrored scores | Solar Fire severity table |
| Declination parity | `tests/property/test_declination_parity.py` | Parallel and contra-parallel produce equal magnitude opposite sign | FK6 declination aspects |
| Midpoint invariants | `tests/property/test_midpoint_invariants.py` | Midpoint longitudes remain consistent across wrap boundaries | Solar Fire midpoint exports |
| Determinism snapshot | `tests/regression/test_golden_events.py` | Golden JSONL must match runtime output exactly | Golden dataset |

## Cross-Backend Parity

- Compare Swiss Ephemeris output to Skyfield within tolerance defined in `docs/module/providers_and_frames.md`.
- QA command: `pytest tests/parity --swiss-ephem-cache ~/.astroengine/ephemeris/de441`.
- Report differences in `observability/parity_report.json` including dataset URNs.

## Performance Targets

| Scenario | Target | Measurement method | Data source |
| -------- | ------ | ------------------ | ----------- |
| 30-day transit window (Venus Cycle profile) | ≤ 2.5 seconds per evaluation on reference hardware (Intel i7-1185G7) | Benchmark harness `python -m astroengine.benchmarks.transit_window` | Performance log parquet |
| Severity recomputation (1,000 events) | ≤ 0.6 seconds | `pytest tests/perf/test_severity_perf.py` flagged with `@pytest.mark.perf` | Observability perf samples |
| Export pipeline (AstroJSON → ICS) | ≤ 0.4 seconds per event | CLI benchmark `astroengine exports bench --channel ics` | ICS template timings |

Performance runs capture environment metadata (Python version, CPU, ephemeris checksum) for auditing.

## Edge-Case Catalog

- **High latitude charts**: Use natal data with |φ| > 66° stored in `profiles/high_latitude_samples.json`. Expect fallback to Whole Sign houses per providers contract.
- **DST transitions**: Validate conversion around 2024-03-10 07:00 UTC using atlas dataset row `atlas://locations/872531`. Compare event times to Solar Fire export `exports/qa/dst_transition.csv`.
- **Retrograde loops**: Check Mars 2022 retrograde dataset `exports/qa/mars_retrograde.csv` ensuring station classification matches Solar Fire.
- **Eclipse visibility**: Confirm NASA path polygons match ICS export metadata for 2024-04-08 total solar eclipse dataset `exports/qa/eclipse_2024.csv`.
- **Declination extremes**: Evaluate out-of-bounds dataset `exports/qa/oob_moon_2025.csv` verifying declination > 24° matches OOB flag.

## Synastry/Composite & Mundane Scenarios

- Synastry: Compare composite chart events using dataset `exports/qa/synastry_composite.csv`; ensure severity scaling respects combined profile weights.
- Mundane: Evaluate national chart `profiles/national/usa_sibly.json` with mundane profile to cross-check ingress events against Solar Fire `exports/qa/mundane_ingresses.csv`.

## Acceptance Workflow

1. Run `pip install -e .[dev]` inside a fresh virtualenv.
2. Execute `python -m astroengine.infrastructure.environment numpy pandas scipy` and attach JSON output to QA report.
3. Run full pytest suite with `pytest -m "not perf"` followed by `pytest -m perf --benchmark-only` on hardware meeting the reference spec.
4. Compare results to thresholds; record pass/fail status in `docs/burndown.md`.
5. Submit QA packet including golden dataset diffs, parity report, and performance logs to governance committee for sign-off.

By adhering to this QA specification, AstroEngine guarantees reproducible outputs derived solely from authenticated data sources.
