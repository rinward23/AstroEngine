# National Charts Registry (Submodule C-041)

**Channels:** `registry.entities`, `registry.versions`, `registry.aliases`,
`charts.resolver`, `charts.confidence`

## Overview

Implements the versioned mundane chart registry for geopolitical entities. Each
entity can host multiple founding or reform moments, all sourced from verifiable
records (Solar Fire exports, national archives, research monographs). The
submodule ensures lossless provenance and supports time-aware resolution of the
applicable chart for analytic scans.

## Data Model & Storage

* **PostgreSQL + PostGIS:** Primary store with schema:
  * `entities` table capturing metadata, ISO codes, and canonical names.
  * `entity_versions` table storing chart moments, coordinates, timezone hints,
    source references, and validity intervals (`valid_from`, `valid_to`).
  * `entity_aliases` table handling multilingual and historical names.
  * `entity_geoms` (shared with geo-temporal submodule) linking versions to
    historical polygons.
* **Indexes:**
  * B-tree on `entity_versions(entity_id, valid_from, valid_to)` for fast
    temporal resolution.
  * GIST on `entity_geoms.geom` (geography) for spatial lookup.
  * GIN on `entities.iso_codes` for ISO/IOC searching.
* **Provenance:**
  * `source_refs` JSONB includes citation id, title, publication date, Solar Fire
    export checksum, and curator contact.
  * `confidence` integer (0–100) with rubric documented in appendix.

## Channels & Subchannels

### `registry.entities`

* Upsert operations for entity metadata.
* Validates ISO codes, ensures dataset references exist under
  `registry/datasets/entities/` with checksums.

### `registry.versions`

* Handles creation of chart versions; enforces UTC timestamps and location
  precision to at least 0.01 arcminutes.
* Generates `tz_hint` using the historical timezone shim, recording source and
  confidence.
* Validates that Solar Fire or equivalent datasets provide natal chart exports
  matching the event timestamp and location.

### `registry.aliases`

* Maintains alias ranges for search and historical labeling; prevents overlap
  conflicts using exclusion constraints.

### `charts.resolver`

* `get_effective_chart(entity_id, at_datetime)` resolves the applicable version
  based on `valid_from/valid_to` and returns chart metadata with provenance.
* `resolve_entity(lat, lon, at_datetime)` delegates to the geo-temporal mapper to
  determine the controlling entity version and returns registry metadata for
  downstream analysis.

### `charts.confidence`

* Computes blended confidence scores combining source reliability, timezone
  certainty, and alias clarity; surfaces in APIs and dashboard tooltips.

## APIs

* `POST /mundane/entities` (bulk upsert via JSONL referencing dataset IDs).
* `GET /mundane/entities/search?q=` supporting text, ISO code, and alias lookup.
* `POST /mundane/entities/{id}/versions` for curated submissions; enforces audit
  trail via `registry_change_log` table.
* `GET /mundane/entities/{id}/chart?at=` returning the resolved version, chart
  metadata, `tz_hint`, and provenance bundle.

## Data Governance

* Required dataset manifests live under `registry/datasets/mundane_registry/` with
  SHA256 checksums and last-verified timestamps.
* Import scripts must reference Solar Fire export filenames and embed the
  original timezone specification used in Solar Fire to avoid drift.
* Any conflicting chart submissions require curatorial review; the API returns
  `409 Conflict` with payload summarizing existing versions.

## Indexing & Caching Strategy

* Redis cache keyed by `entity:{id}:chart:{at_iso}` storing resolution results
  (TTL 1 hour, invalidated on version updates).
* Materialized view `entity_versions_active` for common `valid_to IS NULL`
  lookups, refreshed on ingestion batches.

## Testing & Validation

* Unit tests ensure temporal resolution picks the highest-confidence version
  when overlapping ranges exist.
* Integration tests compare registry output with Solar Fire natal exports for
  canonical countries (e.g., USA 1776-07-04 17:10 LMT).
* Data quality checks verify every version has at least one source reference and
  non-null geolocation.

## Performance Budget

* `GET /mundane/entities/search` must return top 20 results within 150 ms under
  cached conditions.
* `resolve_entity` should complete <50 ms for index-backed lookups.

## Dependencies

* Shares `entity_geoms` with Historical Geo-Temporal Mapping submodule.
* Consumes timezone hints from the `timezone.shim` subchannel until C10 replaces
  it via `tz_bridge` integration.

