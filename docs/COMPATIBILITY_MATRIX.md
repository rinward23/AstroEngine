<!-- >>> AUTO-GEN BEGIN: Compatibility Matrix v1.0 (instructions) -->
Matrix columns:
- astroengine-core, rulesets, profiles, providers(skyfield/swe), exporters, fixed-stars data.
Policy:
- Update on every tagged release; CI checks matrix completeness.
<!-- >>> AUTO-GEN END: Compatibility Matrix v1.0 (instructions) -->

| Module | Submodule | Channel | Rulesets / Schemas | Profiles | Providers (Skyfield/SWE) | Exporters | Fixed-star datasets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chinese | four_pillars | engines | — | profiles/domains/chinese.yaml (BaZi/Zi Wei provenance) | — | — | — |
| chinese | zi_wei_dou_shu | engines | — | profiles/domains/chinese.yaml (BaZi/Zi Wei provenance) | — | — | — |
| data_packs | catalogs | csv | schemas/orbs_policy.json v2025-09-03 | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/dignities.csv (Solar Fire ESSENTIAL.DAT parity)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000)<br>profiles/vca_outline.json v2025-09-18 | — | — | datasets/star_names_iau.csv (IAU WGSN v2024-03)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| data_packs | profiles | catalogue | schemas/orbs_policy.json v2025-09-03 | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/dignities.csv (Solar Fire ESSENTIAL.DAT parity)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000)<br>profiles/vca_outline.json v2025-09-18 | Swiss Ephemeris | — | datasets/star_names_iau.csv (IAU WGSN v2024-03)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| data_packs | schemas | orbs | schemas/orbs_policy.json v2025-09-03 | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/dignities.csv (Solar Fire ESSENTIAL.DAT parity)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000)<br>profiles/vca_outline.json v2025-09-18 | — | — | datasets/star_names_iau.csv (IAU WGSN v2024-03)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| developer_platform | agents | toolkits | — | — | — | — | — |
| developer_platform | cli | workflows | — | — | — | — | — |
| developer_platform | codex | access | — | — | — | — | — |
| developer_platform | devportal | surfaces | — | — | — | — | — |
| developer_platform | sdks | languages | — | — | — | — | — |
| developer_platform | webhooks | contracts | — | — | — | — | — |
| esoterica | adapters | optional_tools | — | — | — | — | — |
| esoterica | alchemy | operations | — | — | — | — | — |
| esoterica | chakras | planetary_lineage | — | — | — | — | — |
| esoterica | decans | chaldean_order | — | — | — | — | — |
| esoterica | initiatory_orders | golden_dawn | — | — | — | — | — |
| esoterica | numerology | digits | — | — | — | — | — |
| esoterica | oracular_systems | geomancy | — | — | — | — | — |
| esoterica | oracular_systems | i_ching | — | — | — | — | — |
| esoterica | oracular_systems | runes | — | — | — | — | — |
| esoterica | seven_rays | bailey_lineage | — | — | — | — | — |
| esoterica | tarot | courts | — | — | — | — | — |
| esoterica | tarot | majors | — | — | — | — | — |
| esoterica | tarot | spreads | — | — | — | — | — |
| esoterica | tree_of_life | paths | — | — | — | — | — |
| esoterica | tree_of_life | sephiroth | — | — | — | — | — |
| event_detectors | declination | declination | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | ingresses | house | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | ingresses | sign | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | lunations | lunar | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | lunations | solar | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | overlays | fixed_stars | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | astroengine.exporters.LegacyTransitEvent | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | overlays | midpoints | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | overlays | profections | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | overlays | returns | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| event_detectors | stations | stations | rulesets/transit/ingresses.ruleset.md (schema transit_ingress)<br>rulesets/transit/lunations.ruleset.md (schema transit_lunation)<br>rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) | Swiss Ephemeris | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| integrations | ephemeris_tooling | skyfield | — | — | Skyfield | — | — |
| integrations | ephemeris_tooling | swiss_ephemeris | — | — | Swiss Ephemeris | — | — |
| integrations | python_toolkits | libraries | — | — | — | — | — |
| integrations | vedic_workflows | desktop_suites | — | — | — | — | — |
| integrations | vedic_workflows | panchanga_projects | — | — | — | — | — |
| interop | schemas | json_data | schemas/contact_gate_schema_v2.json<br>schemas/natal_input_v1_ext.json<br>schemas/orbs_policy.json v2025-09-03<br>schemas/result_schema_v1.json<br>schemas/result_schema_v1_with_domains.json | — | — | — | — |
| interop | schemas | json_schema | schemas/contact_gate_schema_v2.json<br>schemas/natal_input_v1_ext.json<br>schemas/orbs_policy.json v2025-09-03<br>schemas/result_schema_v1.json<br>schemas/result_schema_v1_with_domains.json | — | — | — | — |
| jyotish | aspects | graha_yuddha | — | — | — | — | — |
| jyotish | aspects | srishti | — | — | — | — | — |
| jyotish | houses | karakas | — | — | — | — | — |
| jyotish | houses | lords | — | — | — | — | — |
| jyotish | strength | combustion | — | — | — | — | — |
| jyotish | strength | dignity | — | — | — | — | — |
| mayan | calendar | haab | — | — | — | — | — |
| mayan | calendar | lords_of_night | — | — | — | — | — |
| mayan | calendar | tzolkin | — | — | — | — | — |
| mayan | constants | correlation | — | — | — | — | — |
| mundane | cycles | search | rulesets/transit/ingresses.ruleset.md (schema transit_ingress) | — | — | — | — |
| mundane | ingress | solar_ingress | rulesets/transit/ingresses.ruleset.md (schema transit_ingress) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | — |
| narrative | bundles | summaries | — | — | — | — | — |
| narrative | profiles | persona | — | — | — | — | — |
| narrative | timelords | systems | — | — | — | — | — |
| orchestration | multi_agent | workflows | rulesets/transit/scan.ruleset.md (schema transit_event)<br>rulesets/transit/stations.ruleset.md (schema transit_station) | — | Swiss Ephemeris | — | — |
| predictive | derived_charts | harmonics | — | — | Swiss Ephemeris | — | — |
| predictive | derived_charts | midpoints | — | — | Swiss Ephemeris | — | — |
| predictive | directions | contacts | — | — | Swiss Ephemeris | — | — |
| predictive | directions | solar_arc | — | — | Swiss Ephemeris | — | — |
| predictive | progressions | contacts | — | — | Swiss Ephemeris | — | — |
| predictive | progressions | secondary | — | — | Swiss Ephemeris | — | — |
| predictive | relationships | composite | — | — | Swiss Ephemeris | — | — |
| predictive | relationships | synastry | — | — | Swiss Ephemeris | — | — |
| predictive | returns | lunar | — | — | Swiss Ephemeris | — | — |
| predictive | returns | solar | — | — | Swiss Ephemeris | — | — |
| predictive | vedic_gochar | alerts | — | — | Swiss Ephemeris | — | — |
| predictive | vedic_gochar | transits | — | — | Swiss Ephemeris | — | — |
| predictive | vedic_gochar | triggers | — | — | Swiss Ephemeris | — | — |
| providers | cadence | profiles | — | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/base_profile.yaml. | Skyfield | — | — |
| providers | ephemeris | plugins | — | — | Skyfield<br>Swiss Ephemeris | — | — |
| providers | frames | preferences | — | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Skyfield | — | — |
| reference | charts | types | — | — | Swiss Ephemeris | — | — |
| reference | frameworks | systems | — | profiles/vca_outline.json v2025-09-18<br>profiles/vca_outline.json dataset | — | — | — |
| reference | glossary | definitions | schemas/orbs_policy.json v2025-09-03 | profiles/aspects_policy.json (AE Aspects Policy v1.1)<br>profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | — |
| reference | indicators | catalog | — | profiles/aspects_policy.json (AE Aspects Policy v1.1)<br>profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)<br>profiles/dignities.csv (Solar Fire ESSENTIAL.DAT parity)<br>profiles/fixed_stars.csv (FK6/HYG v4.1, J2000)<br>profiles/vca_outline.json v2025-09-18 | — | — | profiles/fixed_stars.csv (FK6/HYG v4.1, J2000) |
| ritual | elections | windows | — | — | — | — | — |
| ritual | filters | void_of_course | — | — | — | — | — |
| ritual | timing | planetary_days | — | — | — | — | — |
| ritual | timing | planetary_hours | — | — | — | — | — |
| tibetan | symbolism | animals | — | — | — | — | — |
| tibetan | symbolism | elements | — | — | — | — | — |
| tibetan | symbolism | parkha | — | — | — | — | — |
| ux | maps | astrocartography | — | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | datasets/star_names_iau.csv (IAU WGSN v2024-03) |
| ux | maps | transit_overlay | — | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | datasets/star_names_iau.csv (IAU WGSN v2024-03) |
| ux | plugins | panels | — | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | datasets/star_names_iau.csv (IAU WGSN v2024-03) |
| ux | timelines | outer_cycles | rulesets/transit/ingresses.ruleset.md (schema transit_ingress) | profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01) | Swiss Ephemeris | — | datasets/star_names_iau.csv (IAU WGSN v2024-03) |
| vca | catalogs | bodies | — | — | — | — | — |
| vca | profiles | domain | — | — | — | — | — |
| vca | rulesets | aspects | — | — | — | — | — |
| vca | uncertainty | corridors | — | — | — | — | — |
| vca | uncertainty | resonance | — | — | — | — | — |
