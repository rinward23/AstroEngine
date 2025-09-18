# AstroEngine Repository Topology & Coordination — v1.0

This document defines the repository layout, responsibilities, and
coordination rules that keep AstroEngine's module → submodule → channel
→ subchannel hierarchy intact while accommodating the large indexed
CSV/SQLite datasets that power SolarFire-compatible workflows. The
guidance below is text-only for Codex automation.

## 1. Naming & Roles

1. **astroengine-core** *(current repo)*
   - Runtime engine, public API (`TransitEngine`, detectors, refinement,
     profiles, exporters), canonical schemas, CLI, deterministic defaults.
   - Ships minimal data-free fixtures; references external datasets via
     indexed loaders to avoid accidental module removal.

2. **astroengine-rulesets** *(new)*
   - Production YAML/JSON rulesets (e.g., `main.yaml`, profile bindings,
     gating DSL examples) referencing indexed CSV/SQLite tables.
   - Includes validation tests against `contact_gate_schema_v2.json` plus
     sample payloads proving data-backed outputs.

3. **astroengine-profiles** *(new)*
   - Orb policies, severity weights, dignity/sect tables, fixed weighting
     presets; changelog records every default adjustment.
   - Publishes as `astroengine-profiles` (pure data + loader helpers).

4. **astroengine-fixed-stars** *(new)*
   - Curated bright-star catalog (`data/stars.parquet` + lite `stars.json`),
     provenance statements, and orb tables for transit modules.
   - Stores licensing notes confirming permissive reuse rights.

5. **astroengine-ephemeris-skyfield** *(new)*
   - Skyfield-based provider plugin conforming to the core provider
     protocol; ships `ephem pull` CLI to manage `de440s` caches.
   - Declares extras: `skyfield`, `jplephem`, `numpy`.

6. **astroengine-ephemeris-swe** *(new, optional)*
   - Swiss Ephemeris provider plugin with licensing caveats.
   - Contains parity tests comparing results to the Skyfield backend.

7. **astroengine-exporters** *(new)*
   - Heavy exporters (Parquet/Arrow, DuckDB/SQLite, external sinks) that
     keep analytics modules isolated from the runtime package.

8. **astroengine-examples** *(new)*
   - Runnable notebooks/scripts demonstrating real-time tracking,
     rule gating, and exporter usage with mock datasets.

9. **astroengine-docs** *(new)*
   - MkDocs/Sphinx documentation site with tutorials, API reference, and
     glossary; published to GitHub Pages.

10. **astroengine-bench** *(new)*
    - Performance, determinism, and regression benchmarks with fixed
      seeds to guard against accidental module regressions.

11. **astroengine-ci-templates** *(new)*
    - Shared GitHub Actions workflows (`workflow_call`) covering lint,
      tests, wheel builds, and releases.

12. **astroengine-datasets** *(new, optional)*
    - Sanitized natal samples (consented or synthetic) plus derived cubes
      for demonstrations; indexed for fast lookups.

## 2. Cross-Repo Versioning & Contracts

- Adopt semantic versions; keep `astroengine-core` at `0.y.z` until the
  API stabilizes.
- Publish a compatibility matrix mapping `astroengine-core` versions to
  the minimum compatible `rulesets` and `profiles` releases.
- Maintain canonical JSON schemas in **core**; mirror read-only copies in
  dependent repos via submodules or release artifacts.
- Breaking changes require paired PRs across affected repos with explicit
  migration notes and dataset provenance updates.

## 3. Packaging & Extras

- `astroengine-core` publishes extras: `skyfield`, `swe`, `parquet`,
  `cli`, `dev`.
- Provider plugins ship independent wheels and expose discovery
  `entry_points` under `astroengine.providers`.
- Data-heavy repos ship as small PyPI data packages or release artifacts
  downloaded on demand with checksum validation.

## 4. CI/CD Baseline

- Every repo runs GitHub Actions with: `ruff` + `black --check`, `mypy`,
  `pytest`; Python 3.11 and 3.12; wheel builds on tags; PyPI or Pages
  publishing as appropriate.
- Pin runner OS, cache dependencies, set `PYTHONUTF8=1` for reproducible
  logs.

## 5. Security & Licensing

- Code released under permissive licenses (MIT/BSD); confirm compatible
  licenses for star catalogs and ephemerides.
- Store provenance files documenting source URL/commit/date for every
  dataset; never ship synthetic or unverifiable values.
- Use GitHub Actions OIDC for publishing; keep secrets out of repos.

## 6. Bootstrap Checklist

1. Create private repositories (`astroengine-rulesets`, `astroengine-profiles`,
   `astroengine-fixed-stars`, `astroengine-ephemeris-skyfield`,
   `astroengine-exporters`, `astroengine-examples`, `astroengine-docs`,
   `astroengine-bench`, `astroengine-ci-templates`) before open sourcing.
2. Initialize each with a `README.md`, `LICENSE`, `.github/workflows/ci.yml`
   (consuming shared templates), and the minimal directory skeletons listed
   above.
3. Preserve a sample ruleset in **core** for tests while moving production
   YAMLs into `astroengine-rulesets`.

## 7. Optional Future Repositories

- **astroengine-web** — Next.js visualization app consuming Parquet/SQLite
  outputs.
- **astroengine-rust-core** — Potential pyo3-backed performance kernels once
  Python baselines stabilize.

## 8. Immediate Action List (10-second sweep)

- [ ] Spin up `astroengine-rulesets`; relocate production YAMLs there while
      retaining a sample set in **core**.
- [ ] Launch `astroengine-profiles` with orb/severity presets and
      dignity/sect tables.
- [ ] Publish `astroengine-ephemeris-skyfield` plugin featuring the `ephem pull`
      helper.
- [ ] Add `astroengine-fixed-stars` with the bright-star dataset and orb table.
- [ ] Wire CI templates across repos and surface the compatibility grid in the
      **core** README.
- [ ] Prepare first tag releases: core `0.1.0`, rulesets `0.1.0`, profiles `0.1.0`.

Adhering to this layout ensures every run sequence derives from traceable
SolarFire-aligned datasets and that no module, submodule, channel, or subchannel
can be unintentionally removed during iterative development.
