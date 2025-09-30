# Historical Geo-Temporal Mapping (Submodule C-044)

**Channels:** `boundaries.versioning`, `boundaries.indexes`, `timezone.shim`,
`timezone.overrides`, `resolver.point_in_time`

## Overview

Resolves latitude/longitude + datetime queries to the appropriate geopolitical
entity version and timezone offset. Provides a best-effort timezone shim until
the dedicated C10 Atlas & Timezone system is integrated, while documenting
confidence levels and data gaps.

## Boundary Management

* `boundaries.versioning` maintains historical polygons (`entity_geoms`) with
  `valid_from/valid_to` ranges aligned to registry versions.
* Sources include CShapes, Natural Earth, and curated historical atlases. Each
  dataset entry records license, edition, and transformation steps.
* Geometry validation ensures polygons are non-self-intersecting and oriented
  correctly (right-hand rule) in WGS84.
* Stores simplified geometries (`geom_simplified`) for rendering while retaining
  high-resolution shapes for analysis.

## Indexing Strategy

* `boundaries.indexes` builds spatial indexes (GIST) on both full and simplified
  geometries.
* Temporal indexing uses exclusion constraints to prevent overlapping validity
  ranges for the same entity version.
* Precomputes tiles via Tippecanoe/PMTiles for Streamlit map consumption; tile
  manifests capture dataset version and bounding boxes.

## Timezone Shim

* `timezone.shim` loads IANA zoneinfo (including backzone) and exposes
  `guess_tz(lat, lon, at)` returning tzid, UTC offset, and confidence.
* Logs when lookups fall back to nearest-neighbor heuristics or Solar Fire
  annotations.
* `timezone.overrides` allows per-entity overrides stored in
  `tz_overrides(entity_version_id, rules, confidence)` referencing published
  historical timezone studies.

## Resolver

* `resolver.point_in_time` combines spatial and temporal lookups to return the
  governing entity version, timezone guess, and confidence rating.
* API `GET /mundane/georesolve?lat=&lon=&at=` returns entity version metadata,
  timezone info, and data sources (polygon set, tz rule).
* Provides fallbacks for oceanic locations with `entity_version_id = NULL` and
  appropriate reason codes.

## Data Integrity & Provenance

* All boundary datasets documented under `datasets/boundaries/` with transformation
  scripts (`scripts/mundane/boundaries_ingest.py`).
* Timezone overrides cite primary sources (e.g., Shanks, Steffen) and include
  scanned references when licensing permits.
* Confidence scoring rubric ranges from `high` (direct dataset alignment) to
  `low` (heuristic guess); stored alongside resolver responses.

## Testing & Validation

* Unit tests compare resolver results against known historical events (e.g.,
  German reunification, USSR dissolution) ensuring correct entity version selection.
* Timezone shim tests confirm offsets match IANA data post-1970 and degrade
  gracefully with warnings for earlier periods.
* Geometry validation tests run via GDAL/GEOS to guarantee topological integrity.

## Performance Targets

* Resolver queries should complete within 40 ms on warm cache.
* Boundary ingestion pipelines must finish under 10 minutes per dataset with
  validation enabled.

## Integration Points

* Shared entity version IDs with National Charts Registry.
* Provides timezone hints and entity resolution to Eclipse, Outer Cycle, and
  Dashboard submodules.
* Exposes metrics (`mundane.geo.resolve_ms`, `mundane.tzshim.confidence`) for
  observability dashboards.

