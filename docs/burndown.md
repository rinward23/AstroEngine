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
| I-10 | Implement event detector runtime for reserved registry paths | Transit Working Group | ⏳ Planned | 2024-07-15 | `astroengine/modules/event_detectors/`, `docs/module/event-detectors/overview.md` | TODO payloads recorded in registry metadata; awaiting indexed datasets |
| I-11 | Backfill mundane ingress dataset ingestion | Mundane Astrology Guild | ⏳ Planned | 2024-07-22 | `astroengine/modules/mundane/`, Solar Fire ingress exports | Registry placeholders and TODO lists committed; ingestion scripts pending |
| I-12 | Finalise narrative bundle persistence and templates | Narrative Collective | ⏳ Planned | 2024-07-29 | `astroengine/modules/narrative/`, `docs/recipes/narrative_profiles.md` | Placeholder channels added; needs provenance logging & regression tests |
| I-13 | Ship UX overlays with documented data sources | UX & Maps Team | ⏳ Planned | 2024-08-05 | `astroengine/modules/ux/`, `docs/module/interop.md` | Registry placeholders recorded; must document atlas/tz datasets before release |

Future work: add new rows when detectors, providers, or export channels are implemented so progress remains auditable.
