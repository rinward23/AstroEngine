# Event Detector Submodules Index

The table below maps the planned detector submodules to their channels and primary documentation. Maintaining the list avoids accidental loss of registry nodes while the implementation work proceeds.

| Submodule | Channels | Primary references |
| --- | --- | --- |
| `stations` | `stations.direct`, `stations.shadow` | `docs/module/event-detectors/overview.md`, `rulesets/transit/stations.ruleset.md` |
| `ingresses` | `ingresses.sign`, `ingresses.house` | `docs/module/event-detectors/overview.md`, `rulesets/transit/ingresses.ruleset.md` |
| `lunations` | `lunations.solar`, `lunations.lunar` | `docs/module/event-detectors/overview.md`, `rulesets/transit/lunations.ruleset.md` |
| `declination` | `declination.oob`, `declination.parallel` | `docs/module/event-detectors/overview.md` |
| `overlays` | `overlays.midpoints`, `overlays.fixed_stars`, `overlays.returns`, `overlays.profections` | `docs/module/event-detectors/overview.md`, `rulesets/transit/scan.ruleset.md` |

When adding new detector families extend this table and update the overview so the governance tooling can confirm the module → submodule → channel → subchannel hierarchy remains intact.
