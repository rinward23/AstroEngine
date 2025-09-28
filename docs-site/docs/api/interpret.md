# Interpretations API (SPEC-B-006)

The Interpretations API evaluates rulepacks against synastry/composite payloads. The docs
are generated from `openapi/plus-interpretations.json` and cover rulepack discovery plus the
`/interpret/relationship` executor.

!!! warning "Rulepack location"
    The service defaults to `core/interpret_plus/samples`. Override `RULEPACK_DIR`
    to point at production-managed rulepacks.

## Example request

```bash
curl -X POST "http://localhost:8000/interpret/relationship" \
  -H "Content-Type: application/json" \
  -d @api/examples/interpret-request.json
```

`interpret-request.json` uses the same hits produced in Cookbook Notebook 05.

<div data-openapi-src="openapi/plus-interpretations.json"></div>
