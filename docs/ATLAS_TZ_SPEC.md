# Atlas & Timezone System (SPEC-10)

*Status: Draft v1.0 — prepared for module → submodule → channel → subchannel
implementation packets.*

## Purpose & Scope

The Atlas & Timezone layer supplies deterministic geospatial and temporal
context for every chart computed by AstroEngine. The system must resolve
locations, historical timezone offsets (including pre‑1970 IANA `backzone`
rules), and governing geo‑political entities while operating on- or offline.
Outputs feed natal, transit, mundane, and horary channels and therefore demand
lossless provenance. Solar Fire exports, Swiss Ephemeris, OpenStreetMap, and
official boundary archives (e.g., Natural Earth, CShapes) serve as primary data
sources; synthetic values are prohibited.

## Requirements Traceability

### Must Have (M)

1. **C‑101 Historical TZ Engine** — Resolve timezone IDs and UTC offsets for any
   `(lat, lon, at)` instant, including rules prior to 1970. Provide conversions
   between local civil time and UTC with explicit daylight saving gap/fold
   handling and auditing utilities.
2. **C‑102 Location Disambiguation UI** — Deliver a fuzzy search interface that
   clarifies duplicates via geo context, population, and an interactive map
   preview. Results surface timezone previews derived from live data.
3. **C‑103 Geo‑Political Change Logic** — Determine the governing country and
   administrative region for `(lat, lon, at)` and stamp chart metadata with the
   correct entity version plus provenance.
4. **C‑104 Offline Cache & Sync** — Package atlas assets (timezone transitions,
   polygons, gazetteer tables, historical boundaries) into versioned bundles
   that clients can download, verify, and incrementally update.

### Should Have (S)

* Local Mean Time (LMT) fallback where no formal timezone rule exists; emit a
  confidence score and provenance flag.
* Modular geocoder adapters that expose identical request/response envelopes for
  offline parquet indices and online sources such as Nominatim. Ranking is
  pluggable and profile aware.

### Could Have (C)

* Multilingual address parsing with transliteration support and reverse-
  geocoding heatmap hints for ambiguous contexts.

## Architectural Overview

* **Runtime Stack** — Python 3.11+, FastAPI services under `/atlas/*`, PostgreSQL
  15 with PostGIS for spatial queries, Redis for cache and background jobs, and
  Streamlit for the operator UI.
* **Module Layout** — The `atlas` module splits into `tz_engine`, `geocoder`,
  `georesolve`, and `bundle_manager` submodules. Each submodule owns multiple
  channels (e.g., API, CLI, UI) and subchannels (e.g., offline sync vs. online
  probe) to align with repository-wide organization rules.
* **Data Governance** — All referenced datasets must ship with checksums,
  licensing notes, and source links. The ingestion layer records Solar Fire CSV
  extract versions, IANA tzdb release IDs, OpenStreetMap planet extracts
  timestamps, and boundary dataset editions (Natural Earth 5m, CShapes 2022, or
  equivalent).

### Component Responsibilities

| Component | Description | Key Inputs | Key Outputs |
|-----------|-------------|------------|-------------|
| TZ Engine | Spatial lookup of timezone ID, historical offset resolution, gap/fold aware conversions, auditing utilities. | `(lat, lon, at)` or `(local_dt, tzid)`; tz polygons; transitions table; overrides. | `tzid`, offset seconds, DST flag, abbreviation, source provenance, confidence. |
| Geocoder | Fuzzy search and ranking with multi-source adapters and bias controls. | Query string, optional filters, bounding boxes, `at` date. | Ordered candidates with admin hierarchy, population, map preview token, tz preview. |
| Geo-Political Mapper | Temporal polygon lookup for country/admin1 boundaries; returns governing entity versions. | `(lat, lon, at)`; versioned boundary geometries. | Country and region IDs with validity ranges, source citations, entity lineage. |
| Bundle Manager | Builds, verifies, and applies offline bundles with delta update support. | Latest datasets, checksum manifest, prior bundle state. | Signed bundle archives, delta manifests, verification reports. |

## Data Assets & Provenance

1. **Timezone Definitions** — Directly ingest IANA tzdb source (including
   `backzone`) to populate `tz_transitions`. Maintain release parity with
   `tzdata` packages and document release notes. Local anomalies (municipal rules
   or colonial deviations) are stored in `tz_overrides` with citations (government
   gazettes, historical almanacs).
2. **Timezone Polygons** — Use curated canonical polygons (such as `tz_world`
   updates) converted to WGS84 multipolygons. Record the provider, publication
   date, and simplification tolerances. Edge buffers are tracked to mitigate
   coastline ambiguity.
3. **Gazetteer** — Primary offline index derived from GeoNames exports enriched
   with Solar Fire place catalogs. Each row stores alternate names, population,
   admin hierarchy, and bounding boxes. Licensing notes for GeoNames (CC BY 4.0)
   and Solar Fire data (proprietary) must be cited.
4. **Historical Boundaries** — Source shapefiles or GeoParquet data with
   `valid_from/valid_to` attributes (e.g., CShapes v0.7, WHKMLA). Transform to
   PostGIS geography and maintain snapshots for audit reproducibility.
5. **Checksums & Indexes** — All bundles include SHA256 digests. Parquet/PMTiles
   layers use tile or index schemes enabling bounded queries (quadkeys, Hilbert
   curves) for fast lookups without scanning entire files.

## C‑101 Historical Timezone Engine Specification

1. **Spatial Resolver** — `tzid_at(lat, lon)` performs a PostGIS intersect query
   against `tz_polygons`. Boundary cases fall back to centroid proximity or a
   buffered contains check. Multi-polygon matches return the zone with the
   highest intersection area.
2. **Transition Lookup** — `offset_at(tzid, dt_utc)` selects the latest record in
   `tz_transitions` where `t_utc ≤ dt_utc`. For instants ≥ 1970‑01‑01, use the
   compiled `zoneinfo` blob for minimal latency. For pre‑1970 instants, consult
   parsed transitions derived from the same tzdb release to guarantee parity.
3. **Gap/Fold Handling** — `local_to_utc` detects non-existent times (DST
   spring-forward gaps) and ambiguous folds. Policies (`gap: raise|post|pre`,
   `fold: earliest|latest|flag`) are configurable per channel. Responses include
   diagnostics describing which transitions triggered the policy.
4. **UTC→Local Conversion** — `utc_to_local` returns `datetime` objects annotated
   with the PEP‑495 `fold` flag when ambiguous. Abbreviations and DST state are
   relayed for UI display and logging.
5. **Local Mean Time Fallback** — When `tzid` is undefined for an historical
   instant, compute LMT as `round_to_minute(lon * 4 minutes)` with explicit
   `source="LMT"` and `confidence="low"`. Provide warnings so charts can surface
   the reduced certainty.
6. **Auditing Tools** — Ship scripts comparing `zoneinfo` offsets against parsed
   transitions for sampled instants, plus regression fixtures for known edge
   cases (e.g., 1895 Chile transition, 1916 Irish war-time change). Audits must
   log the dataset release ID and sample coordinates.

## C‑102 Location Disambiguation Interface

* **Query Parsing** — Accept free-text queries with optional `country`, `admin1`,
  bounding box bias, and `at` (for historical names). Apply transliteration and
  Unicode normalization before scoring.
* **Scoring Factors** — Combine string similarity (trigram distance), population
  weight, admin level priority, distance to bias center, and historical name
  validity at `at`. Provide explainability data for each candidate.
* **Streamlit UI** — Search tab lists ranked results with country flags (derived
  from ISO 3166-1 alpha-2), admin path breadcrumbs, and population. A map preview
  (Leaflet/MapLibre) pans to the candidate location. Hover details show current
  timezone offset computed via the TZ engine.
* **API Contract** — `GET /atlas/geocode` returns JSON containing candidate IDs,
  coordinates, timezone preview, geo-political context, and dataset provenance.

## C‑103 Geo-Political Change Logic

* **Boundary Resolution** — For `(lat, lon, at)`, query `boundaries` for entries
  where `valid_from ≤ at < valid_to`. Support multiple layers (country, admin1)
  and return null with maritime context when no land entity matches.
* **Versioning & Lineage** — Each entity links to a canonical record containing
  names, ISO codes, and lineage (predecessor/successor). Responses include the
  version ID, validity interval, and citations to the source dataset.
* **Stamping** — Chart metadata records `{country_version, region_version,
  tzid, tz_source, tz_confidence}` to guarantee reproducibility across exports.
  Downstream modules (e.g., ruleset DSL, interop) consume this payload without
  modification to prevent data loss.
* **Explanations** — API responses embed human-readable summaries (e.g.,
  “Poland — Second Republic (1918‑09‑12 to 1939‑09‑01), source: CShapes v0.7”).

## C‑104 Offline Bundle Management

* **Bundle Format** — Archive name `atlas-YYYY.MM.patch.tar.zst` containing
  `tzdb/` (zoneinfo + transitions parquet), `tz_polygons.pmtiles`,
  `places.parquet`, `boundaries.pmtiles`, `overrides.json`, and
  `checksums.json`. Each file lists schema versions and release provenance.
* **Manifest Endpoint** — `GET /atlas/bundle/manifest` returns the latest version
  metadata (semantic version string, created timestamp, file checksums, delta
  availability). Clients compare against local manifest to determine updates.
* **Delta Updates** — Support rsync-style binary deltas or object-level diffs for
  large assets. The bundle manager verifies checksums before promoting a new
  bundle and can roll back on failure.
* **Offline Mode** — CLI and UI expose controls to lock the system into offline
  operation, ensuring all lookups use local caches only. Telemetry records the
  bundle version used for each query.

## Data Model

```text
tz_polygons(id, tzid, geom GEOGRAPHY, source, updated_at)
tz_transitions(tzid, t_utc TIMESTAMPTZ, offset_seconds, isdst BOOL, abbr TEXT)
tz_overrides(id, tzid, from_ts, to_ts, offset_seconds, notes, confidence)
places(place_id, name, ascii_name, alt_names TEXT[], country_iso, admin1,
       admin2, lat, lon, population, fclass, fcode, bbox GEOGRAPHY, sources JSONB)
boundaries(entity_version_id, entity_id, level ENUM('country','admin1'),
           valid_from, valid_to, geom GEOGRAPHY, sources JSONB)
atlas_bundles(version, created_at, manifest JSONB)
```

Indices include PostGIS GIST on geometry columns, B-tree on transition times,
and trigram indexes on place names. Materialized views pre-compute popular city
results for instant UI feedback.

## API Endpoints

* `GET  /atlas/geocode` — Fuzzy search returning ranked candidates, timezone
  preview, and provenance.
* `GET  /atlas/tz/resolve` — Resolve timezone offsets for `(lat, lon, at)`.
* `POST /atlas/time/convert` — Convert between local civil time and UTC with
  configurable gap/fold policies.
* `GET  /atlas/entity/resolve` — Return governing entity versions and sources.
* `GET  /atlas/bundle/manifest` / `GET /atlas/bundle/download` — Bundle metadata
  and archive retrieval.

All endpoints return structured diagnostics, including dataset release IDs and
confidence scores, ensuring downstream consumers can audit responses.

## Observability & Auditing

* Structured logs include `{query_id, tzid, offset_seconds, policy, source,
  bundle_version}`. Metrics track latency distributions for spatial lookups and
  transition resolution.
* Auditing dashboards compare offsets against Solar Fire historical examples and
  highlight discrepancies. Manual review queues capture mismatches.
* Regression fixtures cover DST transitions (fold/gap), high-latitude cases,
  colonial rule changes, and boundary shifts coinciding with timezone changes.

## Testing Strategy

* **Unit Tests** — Validate post-1970 offsets versus Python `zoneinfo`, historical
  offsets against parsed transitions, and LMT fallback calculations.
* **Integration Tests** — End-to-end geocode → timezone → entity resolution using
  curated Solar Fire datasets and sampled historical events. Ensure UI previews
  align with API outputs.
* **Bundle Tests** — Build, download, verify, and promote offline bundles,
  including checksum validation and offline-mode execution.
* **Performance Tests** — Enforce budgets: `tzid_at` ≤ 1 ms (warm), `offset_at`
  ≤ 50 µs post-1970, geocoder top-5 suggestions ≤ 20 ms offline and ≤ 150 ms
  online.

## Implementation Milestones

1. **M1 — TZ Parse & Engine**: Ingest tzdb/backzone, build transitions, implement
   gap/fold policies, deliver auditing scripts.
2. **M2 — Geocoder & UI**: Ship offline index, pluggable adapters, Streamlit
   disambiguation UI with map previews.
3. **M3 — Geo-Political Mapper**: Integrate temporal boundaries, deliver stamping
   helpers, and expose `/atlas/entity/resolve`.
4. **M4 — Offline Bundles**: Produce bundle archives, manifest endpoints, delta
   update logic, and offline-only safeguards.
5. **M5 — Hardening**: Populate overrides, expand regression suites, document
   datasets, and finalize observability pipelines.

## Compliance & Integrity Checklist

* Document dataset provenance, license constraints, and update cadence within the
  bundle manifest and module docs.
* Preserve module hierarchy when adding channels or subchannels; never remove
  existing modules without a signed migration plan.
* Ensure every chart output referencing timezone data records the associated
  bundle version and source dataset identifiers to guarantee reproducibility.

## Appendices

* **A. Data Sources** — IANA tzdb (https://www.iana.org/time-zones), GeoNames,
  Solar Fire place catalogs, OpenStreetMap extracts, Natural Earth, CShapes.
* **B. External Services** — Nominatim (rate-limited, usage policy required),
  MapLibre/Leaflet tiles (document tile source and attribution), Redis (job queue
  persistence policy).
* **C. Future Enhancements** — Address parsing DSL, transliteration library
  integration, reverse-geocoding heatmap hints, advanced map tile caching.

This specification enables downstream engineers to implement the Atlas module
without ambiguity while guaranteeing that every timezone and geo-political output
originates from verifiable, non-synthetic data sources.
