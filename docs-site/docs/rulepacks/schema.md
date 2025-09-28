# Rulepack Schema (SPEC-B-005 + B-013)

```json title="schema.json"
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://astroengine.dev/schemas/rulepack.json",
  "title": "Relationship Rulepack",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "scope", "score", "title", "text", "when"],
    "properties": {
      "id": {"type": "string", "pattern": "^[a-z0-9_-]+$"},
      "scope": {"enum": ["synastry", "composite", "davison"]},
      "score": {"type": "number"},
      "tags": {"type": "array", "items": {"type": "string"}},
      "title": {"type": "string"},
      "text": {"type": "string"},
      "since": {"type": "string", "pattern": "^v\\d+\\.\\d+$"},
      "when": {
        "type": "object",
        "properties": {
          "bodies": {
            "type": ["array", "string"],
            "items": {"type": "string"}
          },
          "aspect_in": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Matches the canonical aspect registry: conjunction, opposition, square, trine, sextile, quincunx, etc."
          },
          "min_severity": {"type": "number", "minimum": 0.0},
          "longitude_ranges": {
            "type": "array",
            "items": {
              "type": "array",
              "items": {"type": "number"},
              "minItems": 2,
              "maxItems": 2
            },
            "description": "Inclusive start, exclusive end degrees (0≤deg<360)."
          }
        },
        "additionalProperties": false
      }
    },
    "additionalProperties": false
  }
}
```

!!! example "DSL Extensions (SPEC-B-013)"
    * `since`: attaches a documentation badge so analysts know which release introduced a rule.
    * `tags`: used by the Report Builder filters and the VS Code snippets catalog.
    * `when.longitude_ranges`: extends composite/davison scopes to reason about placements in
      degree windows instead of aspect hits.

!!! tip "Validation"
    Use `python -m astroengine.ruleset_linter docs-site/docs/rulepacks/examples/basic.yaml`
    to run the static linter described in SPEC-B-005. CI executes this as part of the
    `docs-build` workflow.

See the [examples](examples/) directory for fully annotated packs.
