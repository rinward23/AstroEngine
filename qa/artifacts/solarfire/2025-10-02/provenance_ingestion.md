# Solar Fire Ingestion Evidence — 2025-10-02

This note captures the ingestion artefacts required by burndown Task I-9. All values below are derived from the Solar Fire comparison exports committed to the repository; no synthetic data has been introduced.

## Export manifests

| Export | Source file | SHA-256 |
| --- | --- | --- |
| Cross-engine parity sample (JSON) | `qa/artifacts/solarfire/2025-10-02/cross_engine.json` | `f8bdfe12f7dac0ed559ed46fa9493dcef4953a1fc772b0ddd41757a2f71d22bc` |
| Cross-engine parity report (Markdown) | `qa/artifacts/solarfire/2025-10-02/cross_engine.md` | `76c32afa0da45cf4873e5df13f7c909a23a3ba4bb0af101cd649e5d43c265624` |

Checksums were produced with `sha256sum` on 2025-10-05 and are now pinned in `qa/artifacts/solarfire/expectations.json`; re-run the helper in `python -m qa.validation.report check-solarfire` if either export changes.

## Indexed ingestion summary

- Transit and return samples from `cross_engine.json` were loaded into the Solar Fire comparison harness alongside Swiss Ephemeris generated values. The aggregated statistics appear in `cross_engine.md` and report zero breaches across six samples, confirming lossless ingestion.
- Resulting datasets are catalogued under the runtime registry for provenance: `astroengine/modules/event_detectors/__init__.py` references the Solar Fire benchmarks for transit detectors, and `astroengine/modules/interop/__init__.py` enumerates the extended natal metadata accepted from Solar Fire imports.
- Future Solar Fire exports must append their checksum rows to this table before deployment.

## Operational actions

1. Archive this note with the release bundle so governance can validate the dataset lineage.
2. Re-run the ingestion checksum procedure whenever Solar Fire provides updated transit or return exports, recording the resulting hashes in this document.
