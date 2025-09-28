# Interpret Packs Catalogue

This directory contains versioned interpretation rulepacks used by the
interpretations API. Packs are authored in YAML and validated against
`schema/dsl-extensions.schema.json`.

## Contents

- `packs/` — rulepacks for Saturn, outer-planet themes, luminary emphasis, and
  house overlays.
- `meta/` — higher level compositions that include multiple packs with weights.
- `fixtures/` — canonical synastry hits and composite/davison charts along with
  golden outputs that protect against score drift.
- `tests/` — regression tests that validate pack behaviour using the engine.

## Validation

The packs extend the DSL with:
- aspect family filters (`family`) and explicit `bodiesA`/`bodiesB` selectors.
- `group` definitions for synergy and minimum hit counts.
- `house` constraints for composite/davison overlays including angular checks.
- post-match `boost` and `limit` controls.

Run the pack regression suite with:

```bash
pytest interpret-packs/tests
```
