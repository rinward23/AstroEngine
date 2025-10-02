# UX Module Overview

- **Author**: UX & Maps Working Group
- **Date**: 2025-10-02
- **Scope**: Documents the `ux` module hierarchy reserved in `astroengine/modules/ux/__init__.py` and records the verified datasets required to ship map and timeline overlays without removing any existing modules or channels.

AstroEngine v1.0 treats UX surfaces as first-class registry entries so maps, timelines, and plugin panels can evolve without breaking the module → submodule → channel → subchannel contract. The documents in this directory provide the provenance needed to light up those surfaces using Solar Fire exports, Swiss Ephemeris calculations, and atlas/timezone datasets already tracked in git.

## Registry mapping

The runtime registry reserves the following paths:

- `ux.maps.astrocartography.lines`
- `ux.timelines.outer_cycles.transits`
- `ux.plugins.panels.streamlit`

Each node now links to the specification files listed below. Implementation work must extend the hierarchy in place—never delete or rename these paths.

## Cross-cutting requirements

1. **Data fidelity** – Every overlay must cite a real dataset. Solar Fire derived ephemerides map back to the checksums recorded in `docs/provenance/solarfire_exports.md`. Geospatial layers reference the atlas/timezone assets defined in `docs/ATLAS_TZ_SPEC.md` and `datasets/star_names_iau.csv`.
2. **Deterministic indexing** – Maps and timelines load data through SQLite or Parquet indices keyed by `(body, datetime)` or `(lat, lon)` lookups. Index build steps are recorded in the submodule documents.
3. **Observability** – All UX channels emit structured telemetry (chart identifiers, dataset digests, rendering duration) routed through the observability hooks catalogued in `docs/module/qa_acceptance.md`.
4. **Extensibility** – New subchannels must document their datasets and acceptance criteria before appearing in the registry to ensure downstream tooling never encounters orphaned nodes.

## Submodules

| Submodule | Channel | Spec | Description |
| --- | --- | --- | --- |
| `maps` | `astrocartography.lines` | `docs/module/ux/maps.md` | Real-time astrocartography overlays sourced from Swiss Ephemeris and atlas bundles. |
| `timelines` | `outer_cycles.transits` | `docs/module/ux/timelines.md` | Cycle timelines fed by indexed transit detections and severity bands. |
| `plugins` | `panels.streamlit` | `docs/module/ux/plugins.md` | Streamlit panels that visualise the same datasets with reproducible provenance. |

## Release integration

- Update `docs/burndown.md` when a UX subchannel graduates from “planned” to “shippable”.
- Record dataset refreshes in `docs/governance/data_revision_policy.md` and mirror the checksums into `docs/provenance/solarfire_exports.md` (or the atlas equivalent) to keep QA and release artefacts aligned.
- Ensure acceptance tests cover the rendering code before flipping a channel from placeholder to active inside the registry.
