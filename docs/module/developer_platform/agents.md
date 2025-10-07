# Developer Platform · Agents SDK

- **Author**: Automation Working Group
- **Date**: 2024-10-02
- **Scope**: Submodule `developer_platform/agents` channel `toolkits` describing
  the Python automation SDK exposed via `astroengine.agents.AgentSDK`. The
  deliverable consumes real Solar Fire parity datasets and indexed fixtures to
  construct agent-friendly summaries without removing any runtime modules.

## Inputs

| Input | Location | Notes |
|-------|----------|-------|
| Transit scan outputs | Runtime entrypoints registered under `astroengine.modules` | Reuses the same scan functions invoked by the CLI (`run_scan_or_raise`). |
| Timeline fixtures | `docs-site/docs/fixtures/timeline_events.json` | Canonicalised event samples used to verify normalisation logic. |
| Swiss Ephemeris parity report | `qa/artifacts/solarfire/2025-10-02/cross_engine.json` | Provides dataset identifiers and provenance hashes surfaced in agent summaries. |
| Registry metadata | `astroengine/modules/**` | Ensures module → submodule → channel linkage remains intact for discovery APIs. |

## Outputs

| Artefact | Distribution | Description |
|----------|--------------|-------------|
| `astroengine.agents.AgentSDK` | Included in the core Python package | Class exposing registry discovery, scan orchestration, and context building for automation agents. |
| `AgentScanResult` + `AgentEvent` | Python data structures | Normalised representations used by the SDK to guarantee no data loss when forwarding events to LLM pipelines. |
| Registry wiring | `developer_platform.agents.toolkits.python` | Channel metadata linking documentation, datasets, and runtime modules. |

## Feature Overview

1. **Registry discovery** – `AgentSDK.describe_path()` and
   `AgentSDK.registry_snapshot()` proxy the codex helpers so agents can explore
   the module hierarchy without duplicating the registry logic. The helper keeps
   the module → submodule → channel → subchannel structure intact.
2. **Transit orchestration** – `AgentSDK.scan_transits()` forwards parameters to
   `run_scan_or_raise` and produces an `AgentScanResult`. Each event is
   normalised into an `AgentEvent` that preserves timestamps, moving/target
   bodies, optional aspect/orb data, and raw metadata. No synthetic events are
   emitted: the helper refuses to coerce payloads lacking timestamps or body
   identifiers.
3. **Context building** – `AgentSDK.build_context()` aggregates counts by aspect
   and moving body, collects profile/natal IDs from metadata, and emits dataset
   references (e.g., `docs-site/docs/fixtures/timeline_events.json`,
   `qa/artifacts/solarfire/2025-10-02/cross_engine.json`). This allows LLM
   callers to cite the exact files shipped with the repository when summarising
   scans.
4. **Dataset resolution** – `AgentSDK.resolved_files()` mirrors
   `codex.resolved_files` so agents can open documentation and CSV/JSON fixtures
   directly. This guarantees end-to-end traceability from any automated
   response back to the source datasets.

## Python Toolkit {#python}

```python
from astroengine.agents import AgentSDK

sdk = AgentSDK()
result = sdk.scan_transits(
    start_utc="2024-02-01T00:00:00Z",
    end_utc="2024-02-10T00:00:00Z",
    moving=["Mars"],
    targets=["Saturn"],
)
context = sdk.build_context(result)
```

The scan uses the same entrypoints as the CLI (`astro scan aspects`) and will
surface the `(module, function)` tuple when the underlying runtime returns
events. Metadata attached to each `AgentEvent` includes dataset provenance such
as Solar Fire comparison hashes from
`qa/artifacts/solarfire/2025-10-02/cross_engine.json` when present.

## Observability & Integrity

- Each scan records the utilised entrypoint (e.g.,
  `astroengine.core.transit_engine.scan_window`) in the returned
  `AgentScanResult`. This allows agents to log or audit which runtime produced
  the data.
- The helper rejects payloads missing timestamps, moving bodies, or targets.
  This protects against accidental ingestion of partial or synthetic datasets.
- Dataset references surfaced via `build_context()` are string paths pointing to
  versioned fixtures tracked in git, ensuring reproducibility when agents cite
  results.
- No module deletions or renames occur; the registry entry is additive and keeps
  compatibility with existing developer platform submodules.

## Acceptance Checklist

- [ ] Example notebooks and automation templates updated to import
  `astroengine.agents.AgentSDK`.
- [x] Registry exposes `developer_platform.agents.toolkits.python` with dataset
  references to Solar Fire parity fixtures.
- [x] Unit tests validate event normalisation using
  `docs-site/docs/fixtures/timeline_events.json`.
- [x] Context builder surfaces dataset provenance sourced from
  `qa/artifacts/solarfire/2025-10-02/cross_engine.json` when present.

