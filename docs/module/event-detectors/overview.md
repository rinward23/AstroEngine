# Event Detectors Module Overview

- **Module**: `event-detectors`
- **Maintainer**: Transit Working Group
- **Source artifacts**:
  - `profiles/base_profile.yaml` (orb policies, feature flags, severity weights).
  - `profiles/feature_flags.md` (tabular description of the toggles referenced by the detectors).
  - `rulesets/transit/scan.ruleset.md`, `rulesets/transit/stations.ruleset.md`, `rulesets/transit/ingresses.ruleset.md`, `rulesets/transit/lunations.ruleset.md` (design notes for each detector family).
  - `astroengine/modules/vca/catalogs.py` (canonical body lists used when detectors are wired into the registry).
  - `schemas/shadow_period_event_v1.json`, `schemas/house_ingress_event_v1.json` (JSON Schemas documenting detector payloads).

All detector families described below are wired into the shared registry and exercised by the automated test suite. Swiss Ephemeris drives the astronomical calculations while Solar Fire exports are used as cross-checks; the per-detector notes capture provenance expectations.

## Detector catalogue and inputs

| Detector | Inputs & thresholds | Runtime implementation | Tests |
| --- | --- | --- | --- |
| Stations (retrograde/direct + shadows) | Longitudinal speed sign changes refined with Swiss Ephemeris. Shadow windows reuse the paired station longitudes. Station payloads expose `station_type` to distinguish retrograde vs. direct turns. | `astroengine.detectors.stations.find_stations`, `astroengine.detectors.stations.find_shadow_periods`. | `tests/test_stations_impl.py` |
| Sign ingresses | Ephemeris sampling with adaptive zero-crossing for sign boundaries. | `astroengine.detectors.ingresses.find_sign_ingresses`. | `tests/test_ingress_features.py` |
| House ingresses | Sampling engine applied to natal house cusps supplied by providers. | `astroengine.detectors.ingresses.find_house_ingresses`. | `tests/test_ingresses_mundane.py` |
| Lunations & eclipses | Sun/Moon phase tracking with eclipse visibility checks. | `astroengine.detectors.lunations.find_lunations`, `astroengine.detectors.eclipses.find_eclipses`. | `tests/test_lunations_impl.py`, `tests/test_eclipses_impl.py` |
| Declination aspects & out-of-bounds | Declination parallels/contraparallels and OOB crossings adhering to documented orb tables. | `astroengine.detectors.detect_decl_contacts`, `astroengine.detectors.out_of_bounds.find_out_of_bounds`. | `tests/test_detectors_aspects.py`, `tests/test_out_of_bounds_impl.py` |
| Midpoints & overlays | Midpoint trees, fixed-star contacts, solar/lunar returns, and profection overlays share the transit scan ruleset. | `astroengine.chart.composite.compute_midpoint_tree`, plugin resolvers such as `astroengine.plugins.examples.fixed_star_hits`, `astroengine.detectors.returns.solar_lunar_returns`, `astroengine.timelords.profections.generate_profection_periods`. | `tests/test_progressions_directions_impl.py`, `tests/test_star_names_dataset.py`, `tests/test_timelords.py` |

## Registry topology

The registry exposes the full detector hierarchy used by the runtime:

- `event-detectors/stations` registers `stations.direct` (station exactitudes) and `stations.shadow` (pre/post windows).
- `event-detectors/ingresses` publishes `ingresses.sign.transits` and `ingresses.house.transits`.
- `event-detectors/lunations` exports `lunations.solar.new_and_full` and `lunations.lunar.eclipses`.
- `event-detectors/declination` exposes `declination.oob` and `declination.parallel`.
- `event-detectors/overlays` contains `overlays.midpoints.transits`, `overlays.fixed_stars.contacts`, `overlays.returns.transits`, and `overlays.profections.transits`.

Each leaf node stores the resolver path, event type, backing datasets, and the automated tests that validate the outputs. See `astroengine/modules/event_detectors/__init__.py` for the authoritative wiring.

## Data alignment requirements

- **Solar Fire verification**: Each detector has been cross-checked against Solar Fire scenarios documented in the corresponding ruleset. When updating orb policies or thresholds record the export checksum in the release notes.
- **Indexed lookups**: Stations, ingresses, and lunations read from the Swiss Ephemeris adapter. When parquet/SQLite indices are introduced capture the build command in the data revision log.
- **Profile parity**: When toggles in `profiles/base_profile.yaml` change, update this document and the registry wiring so the module → submodule → channel mapping stays aligned with runtime behaviour.
- **Schema coverage**: Detectors emit dataclasses declared under `astroengine.events` or module-specific payloads. Any schema additions must be registered in `docs/module/interop.md`, with validation tests referencing the appropriate documents (e.g., `schemas/shadow_period_event_v1.json`, `schemas/house_ingress_event_v1.json`).

## Future work

- Expand fixed-star coverage beyond the reference plugin to include the FK6-derived catalogues shipped with production datasets.
