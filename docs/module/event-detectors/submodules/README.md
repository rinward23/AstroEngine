# Event Detector Submodules Index

Each submodule groups a coherent detector family. The table highlights the channels and the canonical documentation that backs each resolver.

| Submodule | Channels | Primary references | Tests |
| --- | --- | --- | --- |
| `stations` | `stations.direct`, `stations.shadow` | `rulesets/transit/stations.ruleset.md`, `docs/module/event-detectors/overview.md` | `tests/test_stations_impl.py` |
| `ingresses` | `ingresses.sign.transits`, `ingresses.house.transits` | `rulesets/transit/ingresses.ruleset.md`, `docs/module/providers_and_frames.md` | `tests/test_ingress_features.py`, `tests/test_ingresses_mundane.py` |
| `lunations` | `lunations.solar.new_and_full`, `lunations.lunar.eclipses` | `rulesets/transit/lunations.ruleset.md` | `tests/test_lunations_impl.py`, `tests/test_eclipses_impl.py` |
| `declination` | `declination.oob`, `declination.parallel` | `rulesets/transit/scan.ruleset.md` (declination sections) | `tests/test_out_of_bounds_impl.py`, `tests/test_detectors_aspects.py` |
| `overlays` | `overlays.midpoints.transits`, `overlays.fixed_stars.contacts`, `overlays.returns.transits`, `overlays.profections.transits` | `rulesets/transit/scan.ruleset.md`, `profiles/fixed_stars.csv`, `docs/module/event-detectors/overview.md` | `tests/test_progressions_directions_impl.py`, `tests/test_star_names_dataset.py`, `tests/test_timelords.py`, `tests/test_timelords_systems.py` |

Extend this table when new detector families are added and keep the references in sync with the registry metadata so governance tooling can audit the hierarchy.
