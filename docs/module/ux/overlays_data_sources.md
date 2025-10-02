# UX Overlays Data Sources

The UX module reserves runtime surfaces for maps, timelines, and plugin panels. This note documents the data sources and indexing expectations now that burndown Task I-13 has closed. Each reference points to material already shipped in the repository so audit trails remain intact.

## Atlas and timezone inputs

- `astroengine/atlas/tz.py` wraps the `timezonefinder` dataset to resolve Olson timezone identifiers from latitude/longitude pairs. Overlay renderers must use `tzid_for`, `to_utc`, and `from_utc` to convert Solar Fire event timestamps into local presentation time without discarding provenance.
- Coordinate metadata for overlays is derived from the Solar Fire comparison exports archived under `qa/artifacts/solarfire/2025-10-02/`. The checksums are tracked in `qa/artifacts/solarfire/2025-10-02/provenance_ingestion.md` to guarantee that overlay timelines reproduce the same event positions used for runtime validation.

## Map overlays

- The `astrocartography` channel registered in `astroengine/modules/ux/__init__.py` renders planetary meridian and paran lines by invoking `astroengine.ux.maps.astrocartography.astrocartography_lines` and the accompanying `local_space_vectors` helper documented in `astroengine/ux/maps/astrocartography.py`. Both routines rely on the star catalogue at `datasets/star_names_iau.csv` and the Solar Fire parity samples at `qa/artifacts/solarfire/2025-10-02/cross_engine.json`. Indexing of planetary lines must occur in SQLite or Parquet tables keyed by latitude/longitude buckets so that Streamlit overlays can paginate efficiently.
- Mundane overlays reuse eclipse and ingress datasets under `docs/module/mundane/submodules/`, especially `eclipse_paths_and_relevance.md`, to maintain parity with the Solar Fire derived charts documented in `qa/artifacts/solarfire/2025-10-02/cross_engine.md`.

## Timeline overlays

- The `outer_cycles` timeline channel is required to index transits using the runtime detectors in `astroengine/modules/event_detectors/__init__.py`. Those detectors already cite the Solar Fire parity benchmarks, ensuring each plotted transit references a recorded dataset.
- Severity bands and narrative annotations are sourced from `astroengine/modules/narrative/` and `profiles/base_profile.yaml`. Overlay code must dereference these files instead of inlining values so updates remain centralized.

## Plugin panels

- Streamlit panels registered under `astroengine/modules/ux/__init__.py` pull data through `ui/streamlit/api.py`, which in turn relies on the runtime registry. Plugins must cite their backing datasets in panel metadata and include checksum references in release notes when new overlays ship.

## Operational guidance

1. When new overlay layers are added, append the dataset location and checksum to this document before enabling the channel in production.
2. Include a pointer to any new indexing artefacts (SQLite migrations, Parquet schemas) so governance reviewers can reproduce the overlay output.
3. Reference this note in release announcements to demonstrate that all UX overlays ship with documented provenance.
