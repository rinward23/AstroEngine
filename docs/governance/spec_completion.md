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

- All constants referenced by detectors or scoring must point to real files (`profiles/base_profile.yaml`, `profiles/dignities.csv`, `profiles/fixed_stars.csv`, `schemas/orbs_policy.json`).
- Schemas must live under `schemas/` and be documented in `docs/module/interop.md`.
- When additional datasets are added, include provenance columns (e.g., `source`, `provenance`) similar to the existing CSV files.

## C. QA gates

- The automated tests listed in `docs/module/qa_acceptance.md` must pass on the reference environment (Python ≥3.10 with `numpy`, `pandas`, `scipy`).
- The environment report produced by `python -m astroengine.infrastructure.environment numpy pandas scipy` should accompany release notes.
- Changes to orb or severity tables require updates to `tests/test_orbs_policy.py`, `tests/test_vca_ruleset.py`, and associated documentation.

## D. Governance artefacts

- Keep `docs/module/` files in sync with the runtime registry to avoid module loss.
- Update `docs/burndown.md` when new deliverables are created or completed.
- Record review outcomes and evidence in `docs/governance/acceptance_checklist.md` during sign-off.

## E. Interoperability

- Every exported payload must validate against the schemas documented in `docs/module/interop.md` using `astroengine.validation.validate_payload`.
- Orb policy data (`schemas/orbs_policy.json`) should remain consistent with the numbers documented in `docs/module/core-transit-math.md`.

## F. Future work tracking

- Planned detectors and provider implementations are documented but not yet shipped. Leave placeholders in the documentation and update this definition once the corresponding code and tests land.
- Any newly introduced feature must add:
  1. Documentation under `docs/module/`.
  2. QA coverage under `tests/`.
  3. An entry in `docs/burndown.md` capturing status and evidence.

Following this definition keeps the documentation, runtime registry, and governance artefacts aligned with the actual repository state.
