# AstroEngine Runtime Guide

AstroEngine organises computational features into a four-level hierarchy:

1. **Module** – top-level capability family (e.g., `gating`, `timelords`, `directions_progressions`, `synastry_composite`).
2. **Submodule** – specific implementation of a capability (e.g., `contact_gating_v2`).
3. **Channel** – data wiring context (e.g., `natal_to_transit`).
4. **Subchannel** – fine-grained variation or dataset slice (e.g., `default`).

A YAML ruleset declares which submodules are available and how they should be wired. The engine resolves the correct
implementation at runtime, injects the channel/subchannel configuration, and produces deterministic outputs backed by the
supplied datasets.

## Ruleset structure

```yaml
version: 0.1.0
modules:
  gating:
    submodules:
      contact_gating_v2:
        channels:
          natal_to_transit:
            subchannels:
              default:
                hard_vetoes:
                  - id: combustion
                    conditions:
                      - column: angular_distance
                        op: lt
                        value: 8
                dampeners:
                  - id: retrograde_mercury
                    factor: 0.5
                    conditions:
                      - column: retrograde
                        op: eq
                        value: true
                boosters:
                  - id: reception
                    factor: 1.25
                    conditions:
                      - column: reception
                        op: eq
                        value: true
        outputs:
          state_table: tables/contact_gate_states.parquet
```

Each submodule can define `outputs`, which the engine resolves relative to the working directory.

## Engine usage

```python
from astroengine.core.engine import AstroEngine
from pathlib import Path

engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"))

payload = {
    "module": "gating",
    "submodule": "contact_gating_v2",
    "channel": "natal_to_transit",
    "subchannel": "default",
    "data": {
        "contacts": contacts_dataframe,
    },
}

result = engine.run(payload)
print(result.state_summary)
```

## Connectors

Dataset connectors translate filesystem assets (CSV, Parquet, or SQLite) into pandas data frames. Custom connectors can be
registered by passing a mapping of names to callables when constructing the engine. Built-in connectors are defined in
`astroengine.connectors` and are safe to extend without modifying existing implementations.

## Outputs

- `tables/contact_gate_states.parquet` – gating state transitions written by `ContactGatingV2`.
- Timelord calculations and directions/progressions return structured pandas data frames for downstream analytics.
- Synastry composite pipelines emit a `CompositeTransitResult` dataclass describing hits and supporting metadata.

All outputs are derived directly from inputs; the engine never fabricates data.
