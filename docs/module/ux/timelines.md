# UX Timelines Specification — Outer Cycle Transits

- **Registry path**: `ux.timelines.outer_cycles.transits`
- **Status**: Documented placeholder (ready for implementation packets)
- **Maintainers**: UX & Maps Working Group
- **Updated**: 2025-10-02

## Purpose

Provide a deterministic feed of outer-planet transit detections for timeline visualisations. The data originates from the event detector infrastructure documented in `docs/module/event-detectors/overview.md` and reuses the Solar Fire calibrated orbs/severity weights defined in `profiles/base_profile.yaml`.

## Data sources

| Asset | Location | Provenance | Usage |
| --- | --- | --- | --- |
| Transit detections | `generated/transits/outer_cycles.jsonl` (planned) | Swiss Ephemeris driven detector runs cross-checked with Solar Fire reports | Primary dataset powering the timeline. |
| Orb/severity policies | `profiles/base_profile.yaml`, `schemas/orbs_policy.json` | Solar Fire default transit profile; see `docs/provenance/solarfire_exports.md` | Determines when a transit is surfaced and how strong it appears on the timeline. |
| Severity matrices | `docs/module/core-transit-math.md` | Harmonises quadratic falloff with Solar Fire comparisons | Supplies thresholds for the colour bands and tooltip ranges. |
| Ruleset DSL | `docs/module/ruleset_dsl.md` | Defines gating phrases and filter expressions | Ensures the timeline filters line up with DSL predicates exposed to end users. |

## Storage format

1. Persist detections as newline-delimited JSON objects sorted by `window_start`. Each object includes: `body`, `aspect`, `target`, `window_start`, `window_end`, `exactitude`, `severity_band`, `source_checksums`.
2. Maintain a DuckDB/Parquet index stored at `datasets/ux/outer_cycle_timelines.duckdb` with covering indices on `(body, window_start)` and `(profile_id, severity_band)`.
3. Record dataset digests and build commands in `docs/governance/data_revision_policy.md` when regeneration occurs.

## Rendering contract

- **Inputs**: `{profile_id, window_start, window_end, severity_min}`.
- **Outputs**: Timeline payload grouped by body with severity bands and provenance metadata (`solar_fire_export_sha`, `environment_sha`).
- **Determinism**: Identical filters must return the same JSON ordering; test by replaying Solar Fire reference windows.
- **Observability**: Emit `astroengine.ux.timeline.render_duration_ms` and attach dataset digests to every log entry.

## Acceptance checklist

1. Execute the detectors per the procedure in `docs/module/event-detectors/overview.md`, capturing Solar Fire comparison CSVs.
2. Run `pytest tests/engine/test_dsl_parse_valid_invalid.py` to ensure timeline filters stay compatible with the ruleset DSL.
3. Generate a 30-day timeline sample and verify severity bands against `docs/module/core-transit-math.md` expected ranges.
4. Document dataset hashes (JSONL + DuckDB) in the release notes alongside the environment report.
