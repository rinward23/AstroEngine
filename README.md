# AstroEngine Schema Contracts

The repository stores JSON schema definitions that mirror the
ruleset appendix contracts referenced by the AstroEngine
runtimes.  Operators can use the helper utilities in
`astroengine.validation` to run doctor-style validations before
launching a scenario.

## Schema directory

All schema payloads live under [`./schemas`](./schemas):

- `result_schema_v1.json` — structure for full run result
  payloads (channels, events, and provenance metadata).
- `contact_gate_schema_v2.json` — captures the gating decisions
  for near-threshold contacts and the evidence that justified
  them.
- `orbs_policy.json` — JSON resource describing the orb policy
  profiles that inform gating and scoring.

The JSON files live outside the Python modules to honor the
append-only ruleset workflow and to keep large data assets out
of the package namespace.

## Validation helpers

Two utility layers support schema validation:

- `astroengine.data.schemas` exposes a registry that resolves the
  JSON files to their on-disk locations.
- `astroengine.validation` provides a self-contained validator that
  understands the subset of JSON Schema used by the appendix contracts.
  Doctor scripts can call `validate_payload("result_v1", payload)` (or any
  other registered schema key) and receive actionable error messages without
  installing third-party packages.

### Running local validations

1. Validate a payload:

   ```python
   from astroengine.validation import validate_payload
   payload = {...}  # assembled from a run
   validate_payload("result_v1", payload)
   ```

2. (Optional) Install `pytest` and run the automated tests (these ship with
   representative sample payloads):

   ```bash
   pip install pytest
   pytest
   ```

The validation helpers are intentionally lightweight so they can
be embedded into existing “doctor” or pre-flight scripts without
risking accidental module removals.

## Related repositories

AstroEngine is evolving into a multi-repository constellation to keep
core runtime logic, data assets, and documentation independently
versioned while guaranteeing that no critical module disappears during
iterative upgrades. The following repositories align with the module →
submodule → channel → subchannel organization goals and provide a
single source of truth for the datasets that drive production runs.

| Repository | Purpose |
| --- | --- |
| `astroengine-core` | Runtime engine, schemas, CLI, and validation helpers (current repo). |
| `astroengine-rulesets` | Production YAML/JSON rule definitions tied to indexed CSV/SQLite datasets. |
| `astroengine-profiles` | Orb policies, severity weights, dignity/sect tables, and related presets. |
| `astroengine-fixed-stars` | Curated bright-star catalog (Parquet/JSON) with provenance and orb tables. |
| `astroengine-ephemeris-skyfield` | Skyfield-based ephemeris provider plugin with cache management helpers. |
| `astroengine-ephemeris-swe` | Swiss Ephemeris plugin with compatibility notes and parity tests. |
| `astroengine-exporters` | Optional exporters (Parquet, Arrow, DuckDB, SQLite) for deterministic analytics. |
| `astroengine-examples` | Runnable notebooks and scripts showcasing real-time tracking workflows. |
| `astroengine-docs` | MkDocs/Sphinx site covering tutorials, reference material, and glossary content. |
| `astroengine-bench` | Performance and determinism regression benchmarks with fixed-seed scenarios. |
| `astroengine-ci-templates` | Shared GitHub Actions workflows for lint/test/build/release pipelines. |
| `astroengine-datasets` (optional) | Sanitized natal samples and derived cubes for consented demonstration runs. |

Each repository maintains provenance for the datasets it references so
that every reported result can be traced back to verifiable, non-synthetic
sources.
