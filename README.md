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

## Repository topology & roles (v1.0)

The AstroEngine ecosystem is organized around a module → submodule → channel → subchannel hierarchy so that no runtime component or data asset is orphaned during upgrades. Each repository below inherits that structure and documents the provenance of any datasets it ships to guarantee that every output is backed by verifiable source material.

| Repository | Role | Key contents | Release channel |
| --- | --- | --- | --- |
| `astroengine-core` | Runtime engine and public API surface (`TransitEngine`, detectors, refinement, profiles, exporters) with canonical schemas and CLI. | `src/astroengine`, `schemas/`, `tests/`, minimal data-free defaults. | PyPI `astroengine` |
| `astroengine-rulesets` | Production YAML/JSON rulesets (e.g., `main.yaml`) and gating DSL examples validated against the core schemas. | `rulesets/*.yaml`, fixtures, schema mirror. | Git tags per ruleset family |
| `astroengine-profiles` | Orb policies, severity weights, dignity/sect tables, and fixed weighting presets aligned with the core module layout. | `profiles/*.json`, schema, changelog. | PyPI `astroengine-profiles` |
| `astroengine-fixed-stars` | Curated bright-star catalog powering transit lookups with RA/Dec, proper motion, and orb tables. | `data/stars.parquet`, `stars.json`, provenance docs. | PyPI data wheel or Git LFS |
| `astroengine-ephemeris-skyfield` | Skyfield-based provider plugin and ephemeris cache helpers (`ephem pull`). | Provider module, cache CLI, docs. | PyPI plugin |
| `astroengine-ephemeris-swe` | Swiss Ephemeris provider plugin with parity tests versus Skyfield. | Provider module, licensing notes, comparison suites. | PyPI plugin (optional) |
| `astroengine-exporters` | Optional heavy exporters (Parquet/Arrow, DuckDB/SQLite sinks) and example pipelines. | `exporters/parquet.py`, `exporters/sqlite.py`, notebooks. | PyPI plugin |
| `astroengine-examples` | Runnable notebooks/scripts demonstrating scans, rule gating, and exporter usage. | `notebooks/*.ipynb`, `examples/*.py`, indexed sample datasets. | GitHub releases |
| `astroengine-docs` | User and API documentation site (MkDocs or Sphinx) covering tutorials, glossary, and references. | Docs sources, theme, publishing workflow. | GitHub Pages |
| `astroengine-bench` | Performance, determinism, and regression benchmarks with fixed-seed datasets. | Benchmark harnesses, scenario fixtures, CI comparators. | GitHub releases |
| `astroengine-ci-templates` | Shared GitHub Actions workflows for linting, testing, releasing, and indexing large datasets. | `.github/workflows/*.yml`, documentation. | Git tags |
| `astroengine-datasets` | Sanitized natal and SolarFire-derived samples (consented or synthetic) plus derived cubes for integration tests. | `datasets/`, manifests, indexing helpers. | GitHub releases or optional PyPI data wheel |

### Module → submodule → channel → subchannel conventions

All repositories adhere to a strict four-tier namespace so that SolarFire-derived datasets, runtime modules, and exporter pipelines stay aligned as the ecosystem grows:

1. **Modules** map to top-level Python packages or dataset families (for example, `astroengine.transits` or the SolarFire natal CSV bundle). A module can never be deleted without a deprecation plan that migrates callers and reindexes data.
2. **Submodules** host cohesive features inside a module (`astroengine.transits.detectors`, `profiles.orbs`). They own the schema contracts that downstream channels consume and therefore must register their assets in the shared schema registry.
3. **Channels** expose externally consumable entry points such as CLI commands, API routes, or dataset exports. Each channel documents the provenance of the data it emits and references an immutable index for every CSV, SQLite, or Parquet file.
4. **Subchannels** represent parameterized views (e.g., "daily transit sweep" vs. "electional window"). Subchannels cannot invent synthetic values; they only filter or aggregate records that exist in the indexed source tables.

The hierarchy applies equally to code and data so that upgrades never strand a rule, schema, or SolarFire ingestion pipeline. Compatibility checks in CI verify that removing a node from the hierarchy fails tests unless an explicit migration is present.

### Dataset indexing & SolarFire ingestion

- Every dataset referenced by a ruleset (CSV, SQLite, Parquet, or external cache) is cataloged in a repository-level manifest that records its checksum, schema version, and the module/submodule responsible for loading it.
- Index builders run as part of CI to generate search accelerators (DuckDB/SQLite indices, Parquet statistics) so real-time tracking queries remain responsive even as the SolarFire dataset footprint expands.
- The ingestion layer maintains append-only logs capturing when a SolarFire export was received, how it was normalized, and which compatibility grid entry certifies it. Operators can always replay these logs to reproduce a given run sequence.
- Validation tests cross-check live data pulls against canonical fixtures to guarantee that all runtime decisions are backed by verifiable source material—never placeholder or synthetic records.

## Cross-repo versioning & contracts

- Adopt semantic versioning. `astroengine-core` remains on the `0.y.z` track until the public API stabilizes; rulesets and profiles version independently so consumers can pin the exact data packages that meet their auditing needs.
- Maintain a compatibility matrix that signals which tagged releases of rulesets and profiles align with each core release. Breaking changes require paired pull requests across affected repositories with a migration note and updated dataset indices.
- Host the canonical JSON schemas inside **core**. Downstream repositories consume them via a read-only mirror (submodule or release artifact) to prevent schema drift while protecting against accidental module removal.

### Compatibility grid (initial release targets)

| astroengine-core | astroengine-rulesets | astroengine-profiles | Notes |
| --- | --- | --- | --- |
| `0.1.0` | `0.1.0` (`main.yaml`) | `0.1.0` (orb/dignity presets) | First public beta; validate SolarFire ingests against indexed datasets before release |

## Packaging & extras

- Publish extras from the core package: `skyfield`, `swe`, `parquet`, `cli`, and `dev` to keep optional heavy dependencies out of the base installation.
- Provider plugins ship as separate wheels that register entry points under `astroengine.providers`, enabling discovery without editing the core module tree.
- Data-focused repositories either release as lightweight PyPI wheels or expose downloadable artifacts with checksums so local tooling can cache and verify them before use.

## CI/CD baseline

- Continuous integration runs `ruff`, `black --check`, `mypy`, and `pytest` on Python 3.11 and 3.12 across all repositories, ensuring that module/submodule/channel/subchannel boundaries remain intact.
- Release workflows build wheels on tags and publish to PyPI (for code/data packages) or GitHub Pages (documentation). Use reusable workflows sourced from `astroengine-ci-templates`.
- Pin runner operating systems, enable dependency caching, and export `PYTHONUTF8=1` to improve reproducibility.

## Security, licensing, and data integrity

- Use permissive licenses (MIT/BSD) for code while verifying that any bundled datasets (e.g., Hipparcos-derived catalogs) meet redistribution requirements.
- Include provenance manifests for every dataset, capturing the upstream URL/commit/date so downstream channels can audit results and confirm integrity before approving a release.
- Store no secrets in the repositories; rely on GitHub Actions OIDC for publishing credentials.
- All runtime outputs must reference indexed, verifiable data—never synthetic or inferred placeholders—so downstream analyses can reproduce the channel/subchannel sequences exactly. Any attempt to emit unindexed data must fail CI and surface an operator alert with the offending module/submodule identifiers.

## Bootstrap instructions

1. Create private repositories (`astroengine-rulesets`, `astroengine-profiles`, `astroengine-fixed-stars`, `astroengine-ephemeris-skyfield`, `astroengine-exporters`, `astroengine-examples`, `astroengine-docs`, `astroengine-bench`, `astroengine-ci-templates`) before opening them to the public.
2. Initialize each repository with a `README.md`, `LICENSE`, `.github/workflows/ci.yml` (importing the shared templates), and the minimal folder layout described above.
3. Migrate production rulesets out of `astroengine-core`, leaving only lightweight samples for tests, and wire the compatibility grid into this README.

## Optional future repositories

- `astroengine-web`: Next.js visualization front-end for transit timelines, consuming Parquet/SQLite exporters.
- `astroengine-rust-core`: Performance-sensitive kernels exposed to Python via `pyo3` once the Python baseline stabilizes.

## 10-second checklist

- [ ] Create `astroengine-rulesets` and relocate production YAMLs there while keeping a sample ruleset in core for test coverage.
- [ ] Launch `astroengine-profiles` with orb/severity presets plus dignity and sect tables tied to the shared schema.
- [ ] Publish the `astroengine-ephemeris-skyfield` provider with an `ephem pull` helper to manage cached ephemerides.
- [ ] Stand up `astroengine-fixed-stars` with a bright-star table, orb indices, and provenance documentation.
- [ ] Connect all repositories to the shared CI templates and maintain the compatibility grid in this README.
- [ ] Plan initial tagged releases: core `0.1.0`, rulesets `0.1.0`, profiles `0.1.0` with verified SolarFire ingest baselines.
