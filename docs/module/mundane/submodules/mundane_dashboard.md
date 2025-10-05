# Mundane Dashboard (Submodule C-045)

**Channels:** `ui.map`, `ui.timeline`, `ui.filters`, `exports.csv`, `exports.geojson`,
`exports.png`, `tiles.vector`, `tiles.cache`

## Overview

Delivers the interactive Streamlit dashboard for mundane analytics. Combines map
visualizations (pydeck/deck.gl) with timeline controls, filters, and export
options. All overlays and exported datasets must originate from registry,
eclipse, cycle, and geo-temporal submodules to preserve data fidelity.

## UI Architecture

* `ui.map` renders base tiles plus overlay layers (eclipse paths, entity
  polygons, triggers). Fetches vector tiles from PostGIS or PMTiles via a FastAPI
  endpoint secured with dataset version parameters.
* `ui.timeline` offers a scrubber linked to the selected date/time; updates map
  overlays and trigger lists in real time.
* `ui.filters` expose toggles for bodies, aspect families, severity thresholds,
  and population-weighted scoring. Filter states persist via URL query params for
  reproducible sessions.

## Export Channels

* `exports.csv` streams table exports (entity triggers, registry versions,
  eclipse impacts) with provenance columns (dataset IDs, source versions).
* `exports.geojson` packages visible map features for GIS workflows; includes
  CRS metadata (WGS84) and timestamp of export.
* `exports.png` captures map snapshots using pydeck screenshot utilities; embeds
  legend, timestamp, and dataset references.

## Vector Tiles & Caching

* `tiles.vector` generates `ST_AsMVT` tiles or serves PMTiles created via the
  `make tiles` pipeline. Tiles include layer metadata (geometry type, dataset
  version) in the MVT metadata block.
* `tiles.cache` leverages Redis to cache rendered tiles and API responses keyed by
  filter set, with invalidation hooks triggered on dataset updates.

## Interactivity & Accessibility

* Tooltips display entity name, chart confidence, eclipse score, and trigger
  details with provenance links.
* Keyboard navigation and high-contrast modes follow `docs/UI_CONVENTIONS.md`.
* Provide fallback table view when WebGL is unavailable.

## Observability

* Emits structured logs for user interactions (layer toggles, exports) with
  anonymized session IDs.
* Collects performance metrics (`mundane.ui.render_ms`, `mundane.export.latency`).

## Testing & QA

* UI integration tests run via Streamlit component harness verifying map loading,
  timeline synchronization, and export button functionality.
* Snapshot tests validate PNG/GeoJSON outputs against golden datasets.
* Accessibility checks (axe-core) ensure WCAG AA compliance for color/contrast.

## Deployment Considerations

* Streamlit app packaged under `ui/streamlit/mundane_app.py`; configured via
  environment variables for API endpoint, tile server URL, and Redis cache.
* Supports offline demo mode using cached MBTiles/PMTiles for workshop scenarios.
* Documented runbook covers dataset refresh, cache warm-up, and export location
  management.

