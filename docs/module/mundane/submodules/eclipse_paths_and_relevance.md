# Eclipse Paths & Relevance (Submodule C-042)

**Channels:** `ingest.besselian`, `ingest.validation`, `geospatial.centerline`,
`geospatial.umbra`, `geospatial.penumbral`, `scoring.area`, `scoring.population`

## Overview

Captures solar and lunar eclipse geometries, stores them as PostGIS geometries,
and computes impact scores for geopolitical entities based on spatial overlap and
population exposure. All eclipse data must originate from published NASA GSFC
Besselian element sets or internally computed Swiss Ephemeris solutions that can
be cross-validated against Solar Fire reports.

## Data Pipeline

1. **Ingestion:** Accept JSON or CSV payloads containing Besselian elements,
   eclipse classification, Saros series, and metadata. Each run records source
   URLs, checksum, and curator.
2. **Geometry Modeling:** Convert Besselian elements into geodesic centerlines
   and polygons for umbra/penumbra footprints using WGS84. Densify polylines at
   ≤1 km intervals to maintain fidelity.
3. **Storage:** Persist geometries in `eclipse_geoms` with geography types.
   Maintain indexes (`GIST`) and metadata for magnitude, duration, and maximum
   eclipse coordinates.
4. **Scoring:** Intersect geometries with entity polygons (version-aware) and
   compute area overlap plus optional population-weighted impacts using raster
   grids (GPW v4 or WorldPop). Scores are normalized (0–100) with component
   breakdown stored in JSONB.

## Channels & Subchannels

### `ingest.besselian`

* Parses NASA/IMCCE/USNO formatted element sets, validates timestamp continuity,
  and stores raw elements in `eclipse_raw` table.
* Supports batch ingestion via asynchronous jobs queued in Redis.

### `ingest.validation`

* Cross-checks computed centerline with published maximum eclipse coordinates.
* Verifies polygon orientation and ensures umbra is contained within penumbra.
* Emits validation reports stored in `eclipse_validation_log` referencing source
  datasets.

### `geospatial.centerline`

* Generates centerline polylines with metadata (velocity, duration, magnitude).
* Provides vector tiles via `ST_AsMVT` for dashboard overlay.

### `geospatial.umbra` & `geospatial.penumbral`

* Constructs polygon geometries for total/annular shadow and partial footprint.
* Handles clipping against coastlines if required for rendering but preserves
  full geometry for analysis.

### `scoring.area`

* Computes area-based impact scores using `ST_Area(ST_Intersection())` with
  geography units (square meters). Normalizes by entity land area and centerline
  proximity bonus.

### `scoring.population`

* Samples population rasters clipped to the intersected polygon, sums
  inhabitants, and applies weighting factors for central path distance.
* Supports caching of raster tiles (Cloud Optimized GeoTIFF) keyed by
  `population:{dataset}:{tile_id}`.

## APIs

* `POST /mundane/eclipses/ingest` accepts dataset references and schedules
  ingestion jobs.
* `GET /mundane/eclipses?from=&to=&type=` returns metadata and availability of
  geometries.
* `GET /mundane/eclipses/{id}/impact` returns ordered impact scores by entity
  version with breakdown of area vs. population components.

## Data Governance

* All Besselian datasets logged with DOI/URL, version, and Solar Fire cross-check
  IDs.
* Raster datasets stored under `datasets/population/` with metadata on resolution,
  projection, and licensing.
* Impact scores must include provenance: geometry version, population raster id,
  scoring algorithm revision.

## Testing & Validation

* Unit tests confirm centerline remains within umbra polygon and endpoints match
  published coordinates.
* Regression tests compare scoring outputs against historical eclipses (e.g.,
  2017-08-21 solar eclipse) with manually verified rankings.
* Performance tests ensure scoring for ~250 entities completes within specified
  budgets (≤300 ms area-only, ≤2 s population-weighted with cache warm).

## Dependencies

* Uses entity polygons and resolver from National Charts Registry & Historical
  Geo-Temporal Mapping.
* Requires PostGIS, GDAL, and rasterio for geospatial operations.
* Integrates with dashboard overlays via vector tile export subchannel.

