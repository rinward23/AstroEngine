# Event Detectors Module Overview

- **Module**: `event-detectors`
- **Maintainer**: Transit Working Group
- **Source artifacts**:
  - `profiles/base_profile.yaml` (orb policies, feature flags, severity weights).
  - `profiles/feature_flags.md` (tabular description of the toggles referenced by the detectors).
  - `rulesets/transit/scan.ruleset.md`, `rulesets/transit/stations.ruleset.md`, `rulesets/transit/ingresses.ruleset.md`, `rulesets/transit/lunations.ruleset.md` (design notes for each detector family).
  - `astroengine/modules/vca/catalogs.py` (canonical body lists used when detectors are wired into the registry).

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

## Performance budgets

Detectors are subject to cold-cache latency limits measured with `pytest-benchmark` on
2025-10-02 (`qa/artifacts/benchmarks/detectors/2025-10-02.json`). Continuous
integration enforces these budgets through `tests/perf/test_detectors_bench.py`,
allowing a 25 % regression window over the recorded medians and means. The
reference capture uses the Swiss Ephemeris cache with explicit invalidation
before each run to reflect worst-case detector latency.

| Detector | Baseline mean (ms) | CI mean budget (ms) | Baseline median (ms) | CI median budget (ms) |
| --- | ---: | ---: | ---: | ---: |
| `find_stations` (`mercury`, `venus`, `mars`, `jupiter`, `saturn`) | 284 | 355 | 272 | 340 |
| `find_shadow_periods` (`mercury`, `venus`) | 196 | 245 | 189 | 236 |
| `find_sign_ingresses` (`sun`, `mercury`, `venus`, `mars`, `jupiter`, `saturn`) | 215 | 269 | 207 | 259 |
| `find_lunations` | 148 | 185 | 142 | 178 |
| `find_eclipses` (global visibility check) | 336 | 420 | 329 | 411 |
| `find_out_of_bounds` (`moon`, `mercury`, `venus`, `mars`) | 241 | 301 | 233 | 291 |

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
- **Schema coverage**: Detectors emit dataclasses declared under `astroengine.events` or module-specific payloads. Any schema additions must be registered in `docs/module/interop.md` and backed by validation tests.

## Future work

- Author JSON schema documents for the new `ShadowPeriod` and house-ingress payloads and link them from `docs/module/interop.md`.
- Expand fixed-star coverage beyond the reference plugin to include the FK6-derived catalogues shipped with production datasets.
