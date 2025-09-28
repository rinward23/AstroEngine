# Relationship API (SPEC-B-003)

The Relationship API exposes `/relationship/synastry`, `/relationship/composite`, and `/relationship/davison`
endpoints that return synastry hits and composite positions. The OpenAPI document is generated via
`python docs-site/scripts/build_openapi.py` and rendered below with Redoc.

!!! info "Authentication"
    The cookbook examples use an unauthenticated dev server. Production deployments enforce
    OAuth2 client credentials; see `ops/deploy.md` for issuer configuration.

## Example request

```bash
curl -X POST "http://localhost:8000/relationship/synastry" \
  -H "Content-Type: application/json" \
  -d @api/examples/synastry-request.json
```

`api/examples/synastry-request.json` matches the dataset used throughout the cookbook.

Download the [Postman collection](relationship.postman.json) or import the
OpenAPI fragment [`openapi/plus-relationship.json`](openapi/plus-relationship.json).

<div data-openapi-src="openapi/plus-relationship.json"></div>
