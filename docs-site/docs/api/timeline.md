# Timeline & Caching APIs (SPEC-B-012 + SPEC-B-015)

The scan endpoints power transit timelines, solar/lunar returns, and caching demonstrations.
`openapi/core-scan.json` documents the `/v1/scan/*` surfaces exported by `astroengine.api_server`.

```bash
curl -X POST "http://localhost:8000/v1/scan/transits" \
  -H "Content-Type: application/json" \
  -d @api/examples/scan-transits-request.json
```

Use `scan-returns-request.json` for return series examples. The caching notebook compares warm
vs cold calls using identical payloads.

<div data-openapi-src="openapi/core-scan.json"></div>
