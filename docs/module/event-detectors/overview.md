# Event Detectors Module Overview

- **Module**: `event-detectors`
- **Maintainer**: Transit Working Group
- **Source artifacts**:
  - `profiles/base_profile.yaml` (orb policies, feature flags, severity weights).
  - `profiles/feature_flags.md` (tabular description of the toggles referenced by the detectors).
  - `rulesets/transit/scan.ruleset.md`, `rulesets/transit/stations.ruleset.md`, `rulesets/transit/ingresses.ruleset.md`, `rulesets/transit/lunations.ruleset.md` (design notes for each detector family).
  - `astroengine/modules/vca/catalogs.py` (canonical body lists used when detectors are wired into the registry).

The runtime registry currently exposes the Venus Cycle Analytics module (`vca`). This document reserves the detector structure that will live alongside it and explains how the existing configuration files back each detector. Referencing the real YAML/JSON/Markdown files listed above ensures that future implementations stay aligned with the recorded thresholds and no module/submodule/channel entries are dropped when the code is added.

## Detector catalogue and inputs

| Detector | Inputs & thresholds | Profile toggle / data source | Design reference |
| --- | --- | --- | --- |
| Stations (retrograde/direct) | Requires longitudinal speed sign changes and natal orb gating defined under `orb_policies.transit_orbs_deg` and `feature_flags.stations`. | `profiles/base_profile.yaml` → `feature_flags.stations.*` and `orb_policies.transit_orbs_deg`. | `rulesets/transit/stations.ruleset.md` |
| Sign ingresses | Uses the same transit orbs with the `ingresses` toggle controlling Moon inclusion and angular gating. | `profiles/base_profile.yaml` → `feature_flags.ingresses.*`. | `rulesets/transit/ingresses.ruleset.md` |
| Lunations & eclipses | Depends on Sun/Moon orbs plus the lunation severity modifiers. Toggle lives under `feature_flags.lunations` and `feature_flags.eclipses`. | `profiles/base_profile.yaml` → `feature_flags.lunations`, `feature_flags.eclipses`. | `rulesets/transit/lunations.ruleset.md` |
| Declination aspects & out-of-bounds | Applies declination orb defaults from `orb_policies.declination_aspect_orb_deg`. | `profiles/base_profile.yaml` → `feature_flags.declination_aspects`, `feature_flags.out_of_bounds`. | `rulesets/transit/scan.ruleset.md` (declination sections) |
| Midpoints & overlays | Use midpoint orb entries and optional lists such as `feature_flags.midpoints.base_pairs`. | `profiles/base_profile.yaml` → `feature_flags.midpoints`, `orb_policies.midpoint_orb_deg`. | `rulesets/transit/scan.ruleset.md` |
| Fixed-star contacts | Draw positions and orbs from `profiles/fixed_stars.csv`; enabled when `feature_flags.fixed_stars.enabled` is true. Requires FK6-derived coordinates and Solar Fire orb defaults. | `profiles/base_profile.yaml`, `profiles/fixed_stars.csv`. | `rulesets/transit/scan.ruleset.md` |
| Returns & profections | Secondary overlays referencing the same profile toggles and natal ephemeris caches. Runtime must point at indexed Solar Fire return tables before emitting events. | `profiles/base_profile.yaml` → `feature_flags.returns`, `feature_flags.profections`. | `rulesets/transit/scan.ruleset.md` |

## Module → submodule → channel placeholders

Until the detector runtime lands, documentation keeps track of the intended registry layout:

- `event-detectors/stations` → channels `stations.direct`, `stations.shadow`.
- `event-detectors/ingresses` → channels `ingresses.sign`, `ingresses.house` (house gating will reuse the provider contract documented in `docs/module/providers_and_frames.md`).
- `event-detectors/lunations` → channels `lunations.solar`, `lunations.lunar`.
- `event-detectors/declination` → channels `declination.oob`, `declination.parallel`.
- `event-detectors/overlays` → channels `overlays.midpoints`, `overlays.fixed_stars`, `overlays.returns`, `overlays.profections`.

These placeholders ensure that the registry retains a deterministic path for each detector and that downstream references (schemas, exporters) can reserve identifiers ahead of implementation.

## Data alignment requirements

- **Solar Fire verification**: Before activating a detector, reproduce the scenario in Solar Fire (or equivalent Swiss Ephemeris
  scripts) and attach the export hash to the detector’s release notes. The runtime should log the provenance URI with every event.
- **Indexed lookups**: Stations, ingresses, and lunations must query indexed ephemeris datasets (SQLite or parquet) rather than raw
  CSV exports to guarantee timely responses during live tracking. Record the index build command in the data revision log.
- **Profile parity**: When toggles in `profiles/base_profile.yaml` change, update the table above and the Markdown rulesets so the
  module → submodule → channel mapping never diverges from the runtime behaviour.
- **Schema coverage**: New detectors should register payload schemas in `docs/module/interop.md` and add validation tests to
  `tests/` so downstream consumers can prove that every emitted event is grounded in real data.

## Outstanding work

- The Markdown rulesets reference schema stubs such as `schemas/events/transit_station.schema.json` that are not yet checked into the repository. When those schemas are authored they must be added to `docs/module/interop.md`, tracked in `docs/burndown.md`, and covered by `astroengine.validation` tests.
- Detector implementations will need to import the body catalogues from `astroengine/modules/vca/catalogs.py` so the module/submodule/channel hierarchy stays consistent with the existing registry.
- Once code lands, add integration tests under `tests/` that exercise each channel using the orbs and toggles documented here.

Documenting these details up front keeps the detector plan aligned with the current environment configuration and prevents accidental loss of module paths during future edits.
