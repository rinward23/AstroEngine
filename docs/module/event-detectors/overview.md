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
| Fixed-star contacts | Draw positions and orbs from `profiles/fixed_stars.csv`; enabled when `feature_flags.fixed_stars.enabled` is true. | `profiles/base_profile.yaml`, `profiles/fixed_stars.csv`. | `rulesets/transit/scan.ruleset.md` |
| Returns & profections | Secondary overlays referencing the same profile toggles. | `profiles/base_profile.yaml` → `feature_flags.returns`, `feature_flags.profections`. | `rulesets/transit/scan.ruleset.md` |

## Module → submodule → channel placeholders

Until the detector runtime lands, documentation keeps track of the intended registry layout:

- `event-detectors/stations` → channels `stations.direct`, `stations.shadow`.
- `event-detectors/ingresses` → channels `ingresses.sign`, `ingresses.house` (house gating will reuse the provider contract documented in `docs/module/providers_and_frames.md`).
- `event-detectors/lunations` → channels `lunations.solar`, `lunations.lunar`.
- `event-detectors/declination` → channels `declination.oob`, `declination.parallel`.
- `event-detectors/overlays` → channels `overlays.midpoints`, `overlays.fixed_stars`, `overlays.returns`, `overlays.profections`.

These placeholders ensure that the registry retains a deterministic path for each detector and that downstream references (schemas, exporters) can reserve identifiers ahead of implementation.

## Outstanding work

- The Markdown rulesets reference schema stubs such as `schemas/events/transit_station.schema.json` that are not yet checked into the repository. When those schemas are authored they must be added to `docs/module/interop.md` and covered by `astroengine.validation` tests.
- Detector implementations will need to import the body catalogues from `astroengine/modules/vca/catalogs.py` so the module/submodule/channel hierarchy stays consistent with the existing registry.
- Once code lands, add integration tests under `tests/` that exercise each channel using the orbs and toggles documented here.

Documenting these details up front keeps the detector plan aligned with the current environment configuration and prevents accidental loss of module paths during future edits.
