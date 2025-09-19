# Specification Burndown Tracker

- **Author**: AstroEngine Program Management Office
- **Updated**: 2024-05-27 (reflects rewritten documentation)

| ID | Task | Owner | Status | Due date | Dependencies | Evidence |
| -- | ---- | ----- | ------ | -------- | ------------ | -------- |
| I-1 | Publish transit math and severity tables | Runtime & Scoring Guild | ✅ Complete | 2024-05-27 | `astroengine/modules/vca/rulesets.py`, `profiles/base_profile.yaml` | `docs/module/core-transit-math.md`, Solar Fire verification notes, `pytest` (`tests/test_vca_ruleset.py`) |
| I-2 | Catalogue bundled data packs | Data Stewardship | ✅ Complete | 2024-05-27 | `profiles/dignities.csv`, `profiles/fixed_stars.csv`, `schemas/orbs_policy.json` | `docs/module/data-packs.md`, `tests/test_orbs_policy.py`, dataset checksums |
| I-3 | Document detector placeholders and hierarchy | Transit Working Group | ✅ Complete | 2024-05-27 | `profiles/base_profile.yaml`, `rulesets/transit/*.ruleset.md` | `docs/module/event-detectors/overview.md`, Solar Fire cross-checks |
| I-4 | Describe provider contract and cadences | Ephemeris Guild | ✅ Complete | 2024-05-27 | `astroengine/providers/__init__.py`, provider design notes | `docs/module/providers_and_frames.md`, parity plan with Solar Fire |
| I-5 | Align interop docs with schemas | Integration Guild | ✅ Complete | 2024-05-27 | Files under `schemas/` | `docs/module/interop.md`, `tests/test_result_schema.py`, `tests/test_contact_gate_schema.py` |
| I-6 | Record QA and release procedures | Quality & Release Guilds | ✅ Complete | 2024-05-27 | `docs/ENV_SETUP.md`, automated test suite | `docs/module/qa_acceptance.md`, `docs/module/release_ops.md`, `pytest` run, Solar Fire comparison artefacts |
| I-7 | Update governance artefacts | Governance Board | ✅ Complete | 2024-05-27 | Docs listed above | `docs/governance/spec_completion.md`, `docs/governance/acceptance_checklist.md` |
| I-8 | Establish data revision workflow | Governance Board | ✅ Complete | 2024-05-27 | `schemas/*`, `profiles/*` | `docs/governance/data_revision_policy.md`, revision log entries |
| I-9 | Capture Solar Fire dataset provenance for runtime outputs | Data Stewardship | 🚧 In progress | 2024-06-15 | Solar Fire exports (transits, returns), planned SQLite indexes | Pending ingestion scripts, checksums to be logged |

Future work: add new rows when detectors, providers, or export channels are implemented so progress remains auditable.
