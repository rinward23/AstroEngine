# UX Plugins Specification — Streamlit Panels

- **Registry path**: `ux.plugins.panels.streamlit`
- **Status**: Documented placeholder (ready for implementation packets)
- **Maintainers**: UX & Maps Working Group
- **Updated**: 2025-10-02

## Purpose

Define the provenance and operational requirements for Streamlit-based panels that visualise AstroEngine datasets. The goal is to guarantee that any shipped panel references real Solar Fire, Swiss Ephemeris, or atlas assets tracked in git and that it can be audited in release notes.

## Data sources

| Asset | Location | Provenance | Usage |
| --- | --- | --- | --- |
| Transit datasets | See `docs/module/ux/timelines.md` | Solar Fire cross-checked detector outputs | Feed interactive charts and severity breakdowns. |
| Astrocartography lines | See `docs/module/ux/maps.md` | Swiss Ephemeris derived Parquet tables | Power map overlays and location lookups inside the panel. |
| Narrative templates | `docs/recipes/narrative_profiles.md`, `astroengine/modules/narrative/` | Narrative Collective validated profiles | Provide textual summaries matching the visual data. |
| Streamlit command | `astroengine-streamlit` entry point (to be exposed in `pyproject.toml`) | Packaging extras: `astroengine[streamlit]` | Launches the panel bundle with datasets mounted read-only. |

## Panel contract

- Panels load datasets via the registry API (`astroengine.modules.registry.get_dataset_uri`) to ensure consistent paths.
- Every rendered view logs `panel_id`, dataset checksums, and `request_id` to align with observability requirements in `docs/module/qa_acceptance.md`.
- Panels must expose a “Data provenance” sidebar referencing `docs/provenance/solarfire_exports.md` and the atlas manifest used in the session.

## Packaging & deployment

1. Define a `streamlit` extra in `pyproject.toml` that pulls `streamlit`, `pydeck`, and `geojson` dependencies alongside `pyswisseph`.
2. Ship example configuration files under `ui_streamlit/` with environment variables pointing to dataset directories (`ASTROENGINE_DATASETS`, `SE_EPHE_PATH`).
3. Document launch instructions in `docs/DEV.md` and add QA smoke tests invoking `python -m streamlit run ui_streamlit/astrocartography.py --server.headless true`.

## Acceptance checklist

1. Confirm datasets listed above have up-to-date checksums in `docs/provenance/solarfire_exports.md` and `docs/ATLAS_TZ_SPEC.md`.
2. Run Streamlit smoke tests and capture screenshots for the release package (store under `docs/performance/ui/` or similar).
3. Verify structured logs emit dataset digests by exercising the panel with `ASTROENGINE_LOG_JSON=1`.
4. Include panel instructions and dataset references in the release notes so downstream integrators can reproduce the visuals.
