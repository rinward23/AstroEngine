# Report Export Endpoints (SPEC-B-014)

Report assembly builds on the composite and Davison APIs provided by the Relationship
service. Use these endpoints to feed the report renderer demonstrated in Cookbook Notebooks 06
and 07.

```bash
curl -X POST "http://localhost:8000/relationship/davison" \
  -H "Content-Type: application/json" \
  -d '{
        "dtA": "1990-07-11T08:00:00Z",
        "dtB": "1992-03-15T20:15:00Z",
        "locA": {"lat_deg": 40.7128, "lon_deg_east": -74.0060},
        "locB": {"lat_deg": 34.0522, "lon_deg_east": -118.2437},
        "bodies": ["Sun", "Moon", "Venus"]
      }'
```

The response returns Davison midpoints used to render the PDF in Notebook 07. Import the
OpenAPI fragment [`openapi/plus-relationship.json`](openapi/plus-relationship.json) for a full
schema reference.

<div data-openapi-src="openapi/plus-relationship.json"></div>
