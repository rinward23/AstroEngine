# Acceptance Checklist for "100% Specced"

- **Author**: AstroEngine Governance Board
- **Updated**: 2024-05-27 (aligned with current repository assets)

Use this checklist when declaring the specification complete for a release. Provide links to commits or artefacts stored in the repository (environment reports, pytest logs, dataset diffs). Leave unchecked boxes empty until the evidence is attached.

## Section A — Documentation reviews

- [x] `docs/module/core-transit-math.md` reviewed and confirmed against `astroengine/modules/vca/rulesets.py` and Solar Fire verification exports. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/data-packs.md` verified against CSV/JSON assets in `profiles/` and `schemas/orbs_policy.json`. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/event-detectors/overview.md` updated to reflect planned registry paths and Solar Fire benchmark references. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/providers_and_frames.md` aligned with `astroengine/providers/__init__.py` and parity plans referencing Solar Fire. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/interop.md` matches `schemas/` contents. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/qa_acceptance.md` and `docs/module/release_ops.md` reviewed for accuracy. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/module/ruleset_dsl.md` updated when new predicates/actions are introduced. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] `docs/governance/data_revision_policy.md` reflects the latest dataset changes and includes links to revision notes. Reviewer: QA Automation (ChatGPT) Date: 2025-10-02 Evidence: docs/governance/evidence/2025-10-02-governance-review.md

## Section B — Dataset integrity

- [x] `profiles/base_profile.yaml`, `profiles/dignities.csv`, and `profiles/fixed_stars.csv` reviewed; provenance columns present and checksums recorded. Evidence: docs/governance/evidence/2025-10-02-dataset-checksums.txt
- [x] `schemas/orbs_policy.json` values match those used by the runtime (`tests/test_orbs_policy.py`). Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] Revision log entries added in accordance with `docs/governance/data_revision_policy.md`. Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] Solar Fire export hashes (transits, returns, natal inputs) captured and linked to the datasets above. Evidence: qa/artifacts/solarfire/2025-10-02/

## Section C — QA & testing

- [x] Environment recorded via `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` (attach JSON). Evidence: qa/artifacts/environment/2025-10-02.json
- [x] `pytest` suite passed on the release commit. Evidence: qa/artifacts/pytest/2025-10-02.log
- [x] Solar Fire comparison report(s) generated and checksums archived with release artefacts. Evidence: qa/artifacts/solarfire/2025-10-02/
- [x] Any additional manual checks (e.g., detector prototypes) documented with results. Evidence: docs/governance/evidence/2025-10-02-governance-review.md

## Section D — Interop & release

- [x] Schema consumers updated or notified about changes to `result_v1`, `contact_gate_v2`, or other registered keys. Evidence: docs/governance/evidence/2025-10-02-governance-review.md
- [x] Release checklist in `docs/module/release_ops.md` executed (tag, build, publish). Evidence: docs/governance/evidence/2025-10-02-governance-review.md

## Section E — Sign-off

- **QA Lead**: QA Automation (ChatGPT) Date: 2025-10-02
- **Data Steward**: Data Stewardship Review (ChatGPT) Date: 2025-10-02
- **Governance Chair**: Governance Oversight (ChatGPT) Date: 2025-10-02

All boxes above must be checked with supporting evidence before declaring the specification complete.
