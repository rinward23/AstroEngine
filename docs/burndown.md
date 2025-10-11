# Specification Burndown Tracker

- **Author**: AstroEngine Program Management Office
- **Updated**: 2025-10-05 (reflects v1 readiness closure)

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
| I-9 | Capture Solar Fire dataset provenance for runtime outputs | Data Stewardship | ✅ Complete | 2024-10-05 | Solar Fire exports (transits, returns), planned SQLite indexes | `qa/artifacts/solarfire/2025-10-02/provenance_ingestion.md`, cross-engine report |
| I-10 | Implement event detector runtime for reserved registry paths | Transit Working Group | ✅ Complete | 2024-07-15 | `astroengine/modules/event_detectors/`, `docs/module/event-detectors/overview.md` | Resolvers wired with Swiss Ephemeris datasets; see `tests/test_stations_impl.py`, `tests/test_ingresses_mundane.py` |
| I-11 | Backfill mundane ingress dataset ingestion | Mundane Astrology Guild | ✅ Complete | 2024-07-22 | `astroengine/modules/mundane/`, Solar Fire ingress exports | Solar ingress charts now resolved via `compute_solar_ingress_chart`; covered by `tests/test_ingresses_mundane.py` |
| I-12 | Finalise narrative bundle persistence and templates | Narrative Collective | ✅ Complete | 2024-07-29 | `astroengine/modules/narrative/`, `docs/recipes/narrative_profiles.md` | Narrative outputs composed by `astroengine.narrative.compose_narrative`; verified by `tests/test_narrative_summaries.py` |
| I-13 | Ship UX overlays with documented data sources | UX & Maps Team | ✅ Complete | 2024-10-05 | `astroengine/modules/ux/`, `docs/module/interop.md` | `docs/module/ux/overlays_data_sources.md`, Solar Fire provenance links |
| I-14 | Publish developer platform specifications (SDKs, CLI, portal, webhooks) | Developer Experience Guild | ✅ Complete | 2024-05-27 | `sdks/*`, `cli/`, `devportal/`, `openapi/v*.json` | `docs/module/developer_platform.md`, `docs/module/developer_platform/*.md`, updated `SPEC_COMPLETION_PLAN.md` |
| I-15 | Canonicalise detector outputs against Solar Fire exports | Quality & Release Guilds | ✅ Complete | 2025-10-06 | `tests/golden/detectors/`, `docs-site/docs/fixtures/` | `tests/test_detector_golden_outputs.py`, `docs/module/qa_acceptance.md` |

Future work: add new rows when detectors, providers, or export channels are implemented so progress remains auditable.
