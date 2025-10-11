# Specification Completion Definition

- **Author**: AstroEngine Governance Board
- **Date**: 2024-05-27 (updated to align with repository state)
- **Scope**: Applies to modules and documentation maintained under `docs/module/`, `docs/governance/`, and the runtime registry in `astroengine/modules`.

The items below describe what "spec complete" means for the assets currently tracked in git. Update the checklist whenever new modules or datasets are introduced.

## A. Documentation coverage

- Map every registry node to a document under `docs/module/`. The current mapping includes:
  - `vca/catalogs` → `docs/module/core-transit-math.md` and `docs/module/data-packs.md`
  - `vca/profiles` → `docs/module/core-transit-math.md`, `docs/module/data-packs.md`, `docs/module/qa_acceptance.md`
  - `vca/rulesets` → `docs/module/core-transit-math.md` and `docs/module/ruleset_dsl.md`
  - Planned `event-detectors/*` → `docs/module/event-detectors/overview.md`
- Any future module must be added to this list before merging so governance can track it.

## B. Inputs, outputs & provenance

- All constants referenced by detectors or scoring must point to real files (`profiles/base_profile.yaml`, `profiles/dignities.csv`, `profiles/fixed_stars.csv`, `schemas/orbs_policy.json`) with Solar Fire or Swiss Ephemeris provenance recorded in the dataset.
- Schemas must live under `schemas/` and be documented in `docs/module/interop.md`.
- When additional datasets are added, include provenance columns (e.g., `source`, `provenance`) similar to the existing CSV files and log the change in `docs/governance/data_revision_policy.md`.

## C. QA gates

- The automated tests listed in `docs/module/qa_acceptance.md` must pass on the reference environment (Python ≥3.10 with `pyswisseph`, `numpy`, `pydantic`, `python-dateutil`, `timezonefinder`, `tzdata`, `pyyaml`, `click`, `rich`, `orjson`, `pyarrow`, `duckdb`). Solar Fire comparison artefacts required by the QA plan must be present for any scoring or detector changes.
- The environment report produced by `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` should accompany release notes.
- Changes to orb or severity tables require updates to `tests/test_orbs_policy.py`, `tests/test_vca_ruleset.py`, associated documentation, and revision entries per `docs/governance/data_revision_policy.md`.

## D. Governance artefacts

- Keep `docs/module/` files in sync with the runtime registry to avoid module loss.
- Update `docs/burndown.md` when new deliverables are created or completed.
- Record review outcomes and evidence in `docs/governance/acceptance_checklist.md` during sign-off.
- Maintain the dataset log in `docs/governance/data_revision_policy.md` whenever schemas or profiles change, including Solar Fire export hashes and index build commands.

## E. Interoperability

- Every exported payload must validate against the schemas documented in `docs/module/interop.md` using `astroengine.validation.validate_payload`.
- Orb policy data (`schemas/orbs_policy.json`) should remain consistent with the numbers documented in `docs/module/core-transit-math.md` and the revision log.

## F. Future work tracking

- Planned detectors and provider implementations documented in the original plan are now implemented. Keep registry wiring (`astroengine/modules/event_detectors/__init__.py`, `astroengine/modules/providers/__init__.py`) in sync with documentation and tests such as `tests/test_event_detectors_module_registry.py`, `tests/test_provider_registry_metadata.py`, and `tests/test_providers_module_registry.py` whenever new features land.
- Any newly introduced feature must add:
  1. Documentation under `docs/module/`.
  2. QA coverage under `tests/`.
  3. An entry in `docs/burndown.md` capturing status and evidence.
  4. A revision entry summarised in `docs/governance/data_revision_policy.md` when datasets are involved.

Following this definition keeps the documentation, runtime registry, and governance artefacts aligned with the actual repository state.
