# Relationship Lab (SPEC-B-004)

The Relationship Lab is the analyst-facing workspace that orchestrates the full stack:
import natal datasets, trigger synastry scans, preview interpretations, and export reports.

## Workflow

1. **Load events** — Drop SolarFire CSV or SQLite exports. The loader indexes the file using the
   module → submodule → channel → subchannel hierarchy to avoid silent module loss.
2. **Configure bodies** — Choose body sets, orb profiles, and aspect catalogs. Defaults align with
   `astroengine.chart.natal.DEFAULT_BODIES` and the `BASE_ASPECTS` harmonic registry.
3. **Execute scans** — Invokes `/relationship/synastry` (B‑003) followed by `/interpret/relationship`
   (B‑006). Responses are cached via the B‑015 strategy described in [`ops/caching.md`](../ops/caching.md).
4. **Curate findings** — Analysts can tag, pin, and reject findings. Actions persist to the
   rulepack author workspace.
5. **Export** — Generate Markdown or PDF bundles (B‑014) and archive the execution metadata.

## Shortcuts

| Action | Shortcut |
| ------ | -------- |
| Run scan | `⌘ + Enter` |
| Toggle composite preview | `C` |
| Toggle Davison preview | `D` |
| Copy Markdown | `⌘ + Shift + C` |

## Resources

* [`cookbook/03_synastry.ipynb`](../cookbook/03_synastry.ipynb) — sample synastry execution.
* [`cookbook/05_interpretations.ipynb`](../cookbook/05_interpretations.ipynb) — applying rulepacks.
