# Acceptance Checklist for "100% Specced"

- **Author**: AstroEngine Governance Board
- **Updated**: 2024-05-27 (aligned with current repository assets)

Use this checklist when declaring the specification complete for a release. Provide links to commits or artefacts stored in the repository (environment reports, pytest logs, dataset diffs). Leave unchecked boxes empty until the evidence is attached.

## Section A — Documentation reviews

- [ ] `docs/module/core-transit-math.md` reviewed and confirmed against `astroengine/modules/vca/rulesets.py` and Solar Fire verification exports. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/data-packs.md` verified against CSV/JSON assets in `profiles/` and `schemas/orbs_policy.json`. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/event-detectors/overview.md` updated to reflect planned registry paths and Solar Fire benchmark references. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/providers_and_frames.md` aligned with `astroengine/providers/__init__.py` and parity plans referencing Solar Fire. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/interop.md` matches `schemas/` contents. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/qa_acceptance.md` and `docs/module/release_ops.md` reviewed for accuracy. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/module/ruleset_dsl.md` updated when new predicates/actions are introduced. Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `docs/governance/data_revision_policy.md` reflects the latest dataset changes and includes links to revision notes. Reviewer: __________________ Date: __________ Evidence: __________________

## Section B — Dataset integrity

- [ ] `profiles/base_profile.yaml`, `profiles/dignities.csv`, and `profiles/fixed_stars.csv` reviewed; provenance columns present and checksums recorded. Evidence: __________________
- [ ] `schemas/orbs_policy.json` values match those used by the runtime (`tests/test_orbs_policy.py`). Evidence: __________________
- [ ] Revision log entries added in accordance with `docs/governance/data_revision_policy.md`. Evidence: __________________
- [ ] Solar Fire export hashes (transits, returns, natal inputs) captured and linked to the datasets above. Evidence: __________________

## Section C — QA & testing

- [ ] Environment recorded via `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` (attach JSON). Evidence: __________________
- [ ] `pytest` suite passed on the release commit. Evidence: __________________
- [ ] Solar Fire comparison report(s) generated and checksums archived with release artefacts. Evidence: __________________
- [ ] Any additional manual checks (e.g., detector prototypes) documented with results. Evidence: __________________

## Section D — Interop & release

- [ ] Schema consumers updated or notified about changes to `result_v1`, `contact_gate_v2`, or other registered keys. Evidence: __________________
- [ ] Release checklist in `docs/module/release_ops.md` executed (tag, build, publish). Evidence: __________________

## Section E — Sign-off

- **QA Lead**: __________________ Date: __________
- **Data Steward**: __________________ Date: __________
- **Governance Chair**: __________________ Date: __________

All boxes above must be checked with supporting evidence before declaring the specification complete.
