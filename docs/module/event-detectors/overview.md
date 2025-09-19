# Event Detectors Module Overview

- **Module**: `event-detectors`
- **Author**: AstroEngine Ruleset Working Group
- **Date**: 2024-05-27
- **Source datasets**: Solar Fire detector exports (`detectors_venus_cycle.sf`), Swiss Ephemeris state vectors (DE441), AstroEngine natal archive indices (`profiles/natal_index.csv`).
- **Downstream links**: runtime registry nodes `astroengine.modules.vca.detectors`, scenario fixtures `tests/detectors/test_event_parity.py`.

This overview documents every detector channel to ensure the runtime registry retains full coverage. Each detector specification references authentic Solar Fire or Swiss Ephemeris data. No synthetic thresholds are introduced; all values align with exportable ephemeris outputs so audit logs can trace events back to real observations.

## Detector Catalogue

| Detector | Signature | Inputs | Outputs | Threshold defaults | Profile toggles | Data requirements |
| -------- | --------- | ------ | ------- | ------------------ | --------------- | ----------------- |
| Planetary Station | `station(event_window, body, profile)` | Ephemeris series (λ, β, speed), natal chart metadata, profile flags | `station_kind`, `in_shadow`, `exact_time`, provenance URN | Velocity crosses zero within ±36h; Δspeed < 0.02°/day | `vca_support`: expands window to ±48h | Swiss Ephemeris `calc_ut`, Solar Fire station tables |
| Sign Ingress | `ingress(body, sign, profile)` | Ephemeris longitude, sign boundaries, natal metadata | `ingress_time`, `sign_index`, `longitude`, `applying_aspects[]` | Report at sign boundary crossing with Δλ wrap < 0.0001° | `vca_tight`: add pre-ingress alert at −1° | Solar Fire ingress report, AstroEngine sign tables |
| Lunation | `lunation(kind, profile)` | Sun/Moon longitudes, phase function, observer location | `lunation_kind`, `exact_time`, `phase_angle`, severity | New/Full: Δλ = 0°/180°; Quarter: Δλ = 90° multiples | `mundane_profile`: adds eclipse flag when | Solar Fire lunation log, NASA eclipse canon |
| Eclipse | `eclipse(kind, profile)` | Saros tables, Besselian elements, Sun/Moon altitude | `eclipse_kind`, `magnitude`, `duration`, `visibility_path` | Magnitude ≥0.25 (partial), ≥0.95 (total) | `mundane_profile`: record path polygon URN | NASA GSFC catalog, Solar Fire eclipse module |
| Combustion | `combustion(body, profile)` | Solar Fire combustion table, Δλ to Sun, velocity | `combustion_state`, `orb`, `phase` | Default: Δλ ≤ 8° for Mercury, 7° for Venus | `vca_tight`: Δλ threshold decreased by 1° | Solar Fire `COMBUST.DEF`, AstroEngine severity policy |
| Out-of-Bounds | `declination_bounds(body, profile)` | Declination series, ecliptic obliquity, natal declination | `oob_flag`, `max_declination`, `entry_time`, `exit_time` | Declination |δ| > ε (23°26′21″) + 0°30′ margin | `mundane_profile`: record daily maxima | Swiss Ephemeris declination output |
| Midpoint Activation | `midpoint_trigger(pair, body, profile)` | Pair midpoints, transit longitude, orb policy | `midpoint_id`, `orb`, `applying_flag` | Orb defaults from `core-transit-math` midpoint rule | `synastry_profile`: add midpoint weighting | Solar Fire midpoint report, AstroEngine orb table |
| Fixed Star Contact | `fixed_star_contact(body, star_id, profile)` | Star RA/Dec, transit RA/Dec, parallax correction | `star_id`, `contact_type`, `orb`, `magnitude` | Longitude orb 1° and declination orb 0°30′ | `vca_support`: widen longitude orb to 1°15′ | FK6 bright star catalogue, Solar Fire fixed star module |
| Declination Parallels | `declination_aspect(body, target, profile)` | Declination of bodies, orb policy table | `aspect_type`, `orb`, `applying_flag` | Orb defaults from declination row in severity matrix | `tight_profile`: reduce orb by 0°10′ | Solar Fire declination aspect export |
| Vertex/Anti-Vertex | `vertex_contact(body, profile)` | Local sidereal time, house system, natal coordinates | `contact_type`, `orb`, `angular_speed` | Orb 2° for conjunctions, 1°30′ for oppositions | `relocation_profile`: include relocated vertex | Solar Fire relocation module, Atlas/TZ dataset |
| Progressions | `progressed_event(kind, profile)` | Secondary progression algorithm, natal chart, ephemeris | `progression_kind`, `exact_time`, `orb`, `profile_id` | Standard day-for-a-year mapping, orb equals natal orb defaults | `synastry_profile`: adds composite triggers | Solar Fire progression tables, AstroEngine natal index |
| Directions | `direction_event(kind, profile)` | Primary direction algorithm, promissor/significator pairs | `direction_kind`, `arc`, `promissor`, `significator` | Semi-arc method, orbs < 1° | `traditional_profile`: prohibits minor aspects | Traditional sources (Sepharial), Solar Fire primary directions |
| Relocation/Astrocartography | `relocation_contact(body, coordinate, profile)` | Relocated chart data, meridian/ascendant lines, atlas index | `contact_type`, `geo_path`, `magnitude`, `profile_id` | Angular lines triggered within 100 km of target coordinate | `travel_profile`: add parans evaluation | Solar Fire astrocartography exports, Atlas/TZ dataset |

## Observability & Provenance

- Every detector emits structured logs containing `detector_id`, `profile_id`, dataset checksum(s), and Solar Fire source URNs (`sf9://detectors_venus_cycle.sf#row=<n>`).
- Metrics publish counts per detector channel and severity band so regressions surface quickly.
- When external datasets (e.g., NASA eclipse tables) update, record the new checksum in `docs/burndown.md` and update the provenance appendix below.

## Provenance Appendix

| Dataset | SHA256 | Maintainer | Last verified |
| ------- | ------ | ---------- | ------------- |
| `detectors_venus_cycle.sf` | `ab3ac3dfc2b540c548c1d864f9ec5c8364cc8614a93f0d81ed8bb1e22c65e4e7` | VCA team | 2024-05-18 |
| Swiss Ephemeris DE441 binaries | `b58f1f7c715142995c3a0c552aa2a2140a7f12225232b3f3f9ee298a045bdd2a` | AstroDienst | 2024-04-30 |
| `profiles/natal_index.csv` | `1fb86e5a8ee86ab1f36ee420d0a55b1ce3ba6e58356f9f79a4e17e45e1a533f3` | AstroEngine data stewardship | 2024-05-15 |
| NASA GSFC eclipse canon 2021–2100 | `d0c8b212cb0f8fd0f070ef569731f4b0a3dbe613e06b9b7f04fbcadd3a5ffb0c` | NASA GSFC | 2024-03-11 |

All detectors remain registered under the `event-detectors` module to prevent accidental removal. Future channel additions should extend this table rather than replace existing rows.
