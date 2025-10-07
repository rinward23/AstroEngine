# Orchestration Module

- **Scope**: Module `orchestration` channel `workflows.solar_fire_tracking_v1`
- **Status**: Planning complete; data-backed plan available for execution tooling.
- **Primary datasets**: `datasets/solarfire/README.md`, `datasets/swisseph_stub/README.md`, `rulesets/transit/scan.ruleset.md`
- **Outputs**: Observability dashboards (`observability/dashboards/engine_scans.json`) and reports described in `docs/recipes/daily_planner.md`.

## Purpose

The orchestration module catalogues cooperative workflows that coordinate multiple
AstroEngine agents. Each workflow maintains the module → submodule → channel →
subchannel lineage so Solar Fire derived datasets remain traceable when
upgrading ingest or reporting automation.

## Multi-agent workflow: `solar_fire_tracking_v1`

| Agent | Responsibilities | Key References |
| --- | --- | --- |
| `ingest_coordinator` | Validate mounted Solar Fire exports, refresh checksum manifests, ensure no datasets are dropped during regeneration. | `datasets/solarfire/README.md`, `docs/module/interop.md`, `docs/governance/data_revision_policy.md` |
| `ephemeris_verifier` | Probe Swiss Ephemeris availability, publish provisioning metadata, prepare cache warm-up routines. | `datasets/swisseph_stub/README.md`, `astroengine/pipeline/provision.py`, `observability/trends/README.md` |
| `transit_reporter` | Execute transit scans backed by verified ephemeris data, emit planner outputs, update observability dashboards. | `rulesets/transit/scan.ruleset.md`, `docs/recipes/daily_planner.md`, `observability/dashboards/engine_scans.json` |

### Data contracts

The workflow references concrete assets rather than synthetic placeholders:

- Solar Fire exports are mounted per `docs/module/interop.md` and tracked in
  `docs/governance/data_revision_policy.md`.
- Swiss Ephemeris availability is documented in
  `astroengine/pipeline/provision.py` and the stub dataset at
  `datasets/swisseph_stub/README.md`.
- Transit scan behaviour is fixed by the ruleset collection under
  `rulesets/transit/` and the planner recipe documented in
  `docs/recipes/daily_planner.md`.

### Observability

Telemetry emitted by the workflow is visualised using
`observability/dashboards/engine_scans.json`, with raw provisioning notes stored
alongside `observability/trends/README.md`. All telemetry must stem from real
runs that consumed verified Solar Fire exports and Swiss Ephemeris data.
