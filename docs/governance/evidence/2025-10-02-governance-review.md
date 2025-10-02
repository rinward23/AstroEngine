# Governance Review — 2025-10-02

## Documentation checks
- `docs/module/core-transit-math.md` confirmed against `astroengine/modules/vca/rulesets.py` and linked profiles/tests. Evidence: in-repo files align (see checklist entries).
- `docs/module/data-packs.md` verified against `profiles/` datasets and `schemas/orbs_policy.json`.
- `docs/module/event-detectors/overview.md` matches registry wiring in `astroengine/modules/event_detectors/__init__.py`.
- `docs/module/providers_and_frames.md` updated to reflect the current provider registry implemented in `astroengine/providers/__init__.py` and module metadata under `astroengine/modules/providers/__init__.py`.
- `docs/module/interop.md` cross-checked with `schemas/*.json` and validation tests.
- `docs/module/qa_acceptance.md` and `docs/module/release_ops.md` reviewed for accuracy.
- `docs/module/ruleset_dsl.md` still mirrors Markdown rulesets and registry expectations.
- `docs/governance/data_revision_policy.md` reviewed; no drift detected.

## Dataset integrity
- SHA-256 checksums recorded in `docs/governance/evidence/2025-10-02-dataset-checksums.txt` for `profiles/base_profile.yaml`, `profiles/dignities.csv`, `profiles/fixed_stars.csv`, and `schemas/orbs_policy.json`.
- `profiles/dignities.csv` and `profiles/fixed_stars.csv` retain provenance/source columns; `profiles/base_profile.yaml` references the same assets.
- `schemas/orbs_policy.json` validated against `tests/test_orbs_policy.py`.
- No new dataset revisions required; policy already documents current workflow.
- Solar Fire parity check executed via Swiss Ephemeris comparison artefacts in `qa/artifacts/solarfire/2025-10-02/`.

## QA artefacts
- Environment report captured at `qa/artifacts/environment/2025-10-02.json`.
- `pytest` log stored at `qa/artifacts/pytest/2025-10-02.log`.
- Solar Fire comparison JSON/Markdown available under `qa/artifacts/solarfire/2025-10-02/`.
- Manual checks limited to dataset/doc verification noted above.

## Release & interop
- Registry and schema consumers reviewed via `docs/module/release_ops.md` and `docs/module/interop.md`; no additional notifications required for this review cycle.
- Release checklist audited with current artefacts (environment report, pytest log, Solar Fire comparison).
