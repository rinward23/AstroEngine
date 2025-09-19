# Specification Burndown Tracker

- **Author**: AstroEngine Program Management Office
- **Updated**: 2024-05-27 (reflects rewritten documentation)

| ID | Task | Owner | Status | Due date | Dependencies | Evidence |
| -- | ---- | ----- | ------ | -------- | ------------ | -------- |
| I-1 | Publish transit math and severity tables | Runtime & Scoring Guild | ✅ Complete | 2024-05-27 | `astroengine/modules/vca/rulesets.py`, `profiles/base_profile.yaml` | `docs/module/core-transit-math.md`, `pytest` (`tests/test_vca_ruleset.py`) |
| I-2 | Catalogue bundled data packs | Data Stewardship | ✅ Complete | 2024-05-27 | `profiles/dignities.csv`, `profiles/fixed_stars.csv`, `schemas/orbs_policy.json` | `docs/module/data-packs.md`, `tests/test_orbs_policy.py` |
| I-3 | Document detector placeholders and hierarchy | Transit Working Group | ✅ Complete | 2024-05-27 | `profiles/base_profile.yaml`, `rulesets/transit/*.ruleset.md` | `docs/module/event-detectors/overview.md` |
| I-4 | Describe provider contract and cadences | Ephemeris Guild | ✅ Complete | 2024-05-27 | `astroengine/providers/__init__.py`, provider design notes | `docs/module/providers_and_frames.md` |
| I-5 | Align interop docs with schemas | Integration Guild | ✅ Complete | 2024-05-27 | Files under `schemas/` | `docs/module/interop.md`, `tests/test_result_schema.py`, `tests/test_contact_gate_schema.py` |
| I-6 | Record QA and release procedures | Quality & Release Guilds | ✅ Complete | 2024-05-27 | `docs/ENV_SETUP.md`, automated test suite | `docs/module/qa_acceptance.md`, `docs/module/release_ops.md`, `pytest` run |
| I-7 | Update governance artefacts | Governance Board | ✅ Complete | 2024-05-27 | Docs listed above | `docs/governance/spec_completion.md`, `docs/governance/acceptance_checklist.md` |

Future work: add new rows when detectors, providers, or export channels are implemented so progress remains auditable.
