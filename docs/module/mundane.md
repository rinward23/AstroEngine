# Mundane Module — SPEC-4 Architecture

**Status:** Draft specification derived from SPEC-4 requirements (Mundane Astrology)

## Purpose

The Mundane module delivers geopolitical and world-event analytics atop AstroEngine's
astrological core. It provides a module → submodule → channel → subchannel structure
that ingests vetted mundane datasets (e.g., Solar Fire exports, historical atlases,
population grids) and exposes real-time dashboards, APIs, and exports without removing
or degrading existing modules.

## Scope & Milestones

The module is partitioned according to SPEC-4 milestones:

1. **M1 Registry & Geo Resolver** – Implements the National Charts Registry and
   historical geo-resolver services.
2. **M2 Eclipse Engine** – Adds eclipse ingestion, path modeling, and impact scoring.
3. **M3 Outer Cycles** – Introduces outer-planet cycle analytics, ingress detection,
   and entity trigger sweeps.
4. **M4 Dashboard** – Publishes the interactive Streamlit dashboard and export suite.
5. **M5 Hardening** – Finalizes caching, vector tile pipelines, QA checks, and
   documentation.

Each milestone corresponds to a submodule spec stored under
`docs/module/mundane/submodules/` and documents the mandatory channels and
subchannels needed for successful implementation.

## Submodule Map

| Submodule | Channels | Description |
|-----------|----------|-------------|
| [National Charts Registry](submodules/national_charts_registry.md) | `registry` → (`entities`, `versions`, `aliases`), `charts` → (`resolver`, `confidence`) | Versioned mundane charts with provenance and chart resolution utilities. |
| [Eclipse Paths & Relevance](submodules/eclipse_paths_and_relevance.md) | `ingest` → (`besselian`, `validation`), `geospatial` → (`centerline`, `umbra`, `penumbra`), `scoring` → (`area`, `population`) | Eclipse geometry ingestion, storage, and country impact scoring. |
| [Outer-Cycle Analytics](submodules/outer_cycle_analytics.md) | `cycles` → (`pairs`, `search`), `ingresses` → (`detection`, `timeline`), `triggers` → (`entity`, `severity`) | Outer-planet cycles, sign ingresses, and entity trigger sweeps. |
| [Historical Geo-Temporal Mapping](submodules/historical_geo_temporal_mapping.md) | `boundaries` → (`versioning`, `indexes`), `timezone` → (`shim`, `overrides`), `resolver` → (`point-in-time`) | Historical boundary resolution and timezone inference shim. |
| [Mundane Dashboard](submodules/mundane_dashboard.md) | `ui` → (`map`, `timeline`, `filters`), `exports` → (`csv`, `geojson`, `png`), `tiles` → (`vector`, `cache`) | Streamlit dashboard, overlay rendering, and export pathways. |

## Data Integrity Guarantees

* Every output must cite deterministic sources (Solar Fire archives, Swiss Ephemeris,
  curated historical datasets). Synthetic or placeholder data is prohibited.
* Large datasets (CSV, SQLite, raster grids) require indexed access paths documented
  within each submodule spec. These include B-tree or GIN indexes, PostGIS spatial
  indexes, raster tiling strategies, and Redis cache keys.
* Provenance metadata (source, version, checksum, confidence) must be stored with
  each record and surfaced in APIs/exports.

## Integration & Dependencies

* **SPEC-0 Engines:** The module reuses aspect/event engines for cycle search,
  ensuring compatibility by exposing adapters within each submodule's channel.
* **C10 Atlas & Timezone System:** Historical timezone fidelity is shimmed locally
  but prepared to delegate to the C10 system via a `tz_bridge` subchannel once
  available.
* **PostgreSQL/PostGIS:** Required for geo-resolver, eclipse geometry, and scoring.
* **Redis:** Provides job orchestration and cache support for long-running scans.
* **Streamlit + pydeck:** Powers the Mundane Dashboard map and timeline overlays.

## Observability & QA

* Structured logs include dataset version IDs, query time ranges, and cache hit
  ratios per channel.
* QA harness references golden Solar Fire exports and published mundane almanacs
  for regression checks.
* Performance budgets and test plans defined in submodule docs feed the CI suites
  under `tests/mundane/` (to be created alongside implementation).

## Change Management

* Additive only: implementing SPEC-4 must not remove existing modules or datasets.
* New datasets must be registered under `registry/datasets/` with checksum manifests
  and ingestion scripts referencing Solar Fire-compatible formats.
* Documentation updates must accompany schema or API changes and remain in sync with
  the module-submodule-channel hierarchy described above.

