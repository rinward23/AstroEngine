# AstroEngine

AstroEngine provides a modular astrology computation framework organised by module → submodule → channel → subchannel. The
engine is driven by YAML rulesets, allowing analysts to swap or extend behaviours without modifying the runtime code. The
current implementation includes contact gating, timelord sequencing, directions/progressions, and synastry composite
pipelines, all designed to work with deterministic, real-world datasets exported from SolarFire and other charting suites.

Key goals:

- **Data integrity** – every computed output is traceable to the source data and configuration that produced it.
- **Extensibility** – new modules and datasets can be registered via the ruleset without replacing existing code.
- **Deterministic testing** – regression fixtures validate each computation path to guard against regressions.

Refer to `docs/astroengine.md` for detailed usage instructions.
