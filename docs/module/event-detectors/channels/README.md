# Event Detector Channels Index

This index mirrors the placeholder registry described in `docs/module/event-detectors/overview.md`. Listing every channel/subchannel pair up front prevents accidental removal once the detector implementations ship.

| Channel | Subchannel(s) | Description | Backing data |
| --- | --- | --- | --- |
| `stations` | `direct`, `shadow` | Retrograde/direct station outputs, including optional pre/post shadow markers. | `profiles/base_profile.yaml` (`feature_flags.stations`, `orb_policies.transit_orbs_deg`), `rulesets/transit/stations.ruleset.md` |
| `ingresses` | `sign`, `house` | Zodiac and house ingress reporting. House support depends on provider metadata documented in `docs/module/providers_and_frames.md`. | `profiles/base_profile.yaml` (`feature_flags.ingresses`) |
| `lunations` | `solar`, `lunar` | New/full/quarter lunations plus optional eclipse flags. | `profiles/base_profile.yaml` (`feature_flags.lunations`, `feature_flags.eclipses`), `rulesets/transit/lunations.ruleset.md` |
| `declination` | `oob`, `parallel` | Declination out-of-bounds and parallel/contraparallel hits. | `profiles/base_profile.yaml` (`feature_flags.declination_aspects`, `orb_policies.declination_aspect_orb_deg`) |
| `overlays` | `midpoints`, `fixed_stars`, `returns`, `profections` | Secondary overlays that reuse the core orb tables. Fixed-star contacts require FK6 coordinates; returns/profections depend on indexed Solar Fire datasets. | `profiles/base_profile.yaml`, `profiles/fixed_stars.csv`, `rulesets/transit/scan.ruleset.md` |

Future updates must append to this table; do not delete rows or rename identifiers without updating the registry wiring and associated documentation.

> **Solar Fire provenance**
> 
> - Station and ingress outputs must store the Solar Fire or Swiss Ephemeris export hash used for verification.
> - Returns and profections should emit the natal dataset checksum to guarantee that runtime narratives cite real chart data.
