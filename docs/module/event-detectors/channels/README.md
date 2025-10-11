# Event Detector Channels Index

The table below mirrors the active registry described in `docs/module/event-detectors/overview.md`. Each entry lists the runtime resolver alongside the key datasets and tests that keep the channel grounded in real Solar Fire comparisons.

| Channel | Subchannel(s) | Resolver(s) | Backing data | Tests |
| --- | --- | --- | --- | --- |
| `stations` | `direct` | `astroengine.detectors.stations.find_stations` | `profiles/base_profile.yaml`, `rulesets/transit/stations.ruleset.md`, Swiss Ephemeris | `tests/test_stations_impl.py` |
| `stations` | `shadow` | `astroengine.detectors.stations.find_shadow_periods` | Same as above, `schemas/shadow_period_event_v1.json` | `tests/test_stations_impl.py` |
| `ingresses` | `sign.transits` | `astroengine.detectors.ingresses.find_sign_ingresses` | `profiles/base_profile.yaml`, `rulesets/transit/ingresses.ruleset.md` | `tests/test_ingress_features.py` |
| `ingresses` | `house.transits` | `astroengine.detectors.ingresses.find_house_ingresses` | Provider house cusps, `docs/module/providers_and_frames.md`, `rulesets/transit/ingresses.ruleset.md`, `schemas/house_ingress_event_v1.json` | `tests/test_ingresses_mundane.py` |
| `lunations` | `solar.new_and_full` | `astroengine.detectors.lunations.find_lunations` | `profiles/base_profile.yaml`, `rulesets/transit/lunations.ruleset.md` | `tests/test_lunations_impl.py` |
| `lunations` | `lunar.eclipses` | `astroengine.detectors.eclipses.find_eclipses` | Same as above | `tests/test_eclipses_impl.py` |
| `declination` | `oob` | `astroengine.detectors.out_of_bounds.find_out_of_bounds` | `profiles/base_profile.yaml`, `rulesets/transit/scan.ruleset.md` | `tests/test_out_of_bounds_impl.py` |
| `declination` | `parallel` | `astroengine.detectors.detect_decl_contacts` | Same as above | `tests/test_detectors_aspects.py` |
| `overlays` | `midpoints.transits` | `astroengine.chart.composite.compute_midpoint_tree` | `profiles/base_profile.yaml`, `rulesets/transit/scan.ruleset.md` | `tests/test_progressions_directions_impl.py` |
| `overlays` | `fixed_stars.contacts` | `astroengine.plugins.examples.fixed_star_hits._detect_fixed_star_hits` | `profiles/fixed_stars.csv`, `rulesets/transit/scan.ruleset.md` (FK6 catalogue, V ≤ 4.5) | `tests/test_star_names_dataset.py`, `tests/test_fixed_stars_analysis.py` |
| `overlays` | `returns.transits` | `astroengine.detectors.returns.solar_lunar_returns` | `profiles/base_profile.yaml`, `rulesets/transit/scan.ruleset.md` | `tests/test_progressions_directions_impl.py` |
| `overlays` | `profections.transits` | `astroengine.timelords.profections.generate_profection_periods` | `profiles/base_profile.yaml`, `rulesets/transit/scan.ruleset.md` | `tests/test_timelords.py`, `tests/test_timelords_systems.py` |

Future updates must append to this table and update the registry wiring in lockstep so downstream audits can confirm the module → submodule → channel → subchannel hierarchy.
