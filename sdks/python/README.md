# AstroEngine Python SDK

The `astro-sdk` package mirrors the workflow described in
`docs/module/developer_platform/sdks.md`. The Poetry configuration lives next
to the generator script so the documented commands run verbatim:

- `poetry install`
- `poetry run python scripts/generate.py --schema ../../openapi/v1.0.json`
- `poetry run pytest sdks/python/tests`

The generator stores release metadata (OpenAPI hash plus dataset fingerprints)
in `CHANGELOG.md` and writes code to `astro_sdk/generated/schema.py`. Tests rely
on the Swiss Ephemeris and Solar Fire stub readmes when the proprietary datasets
are not mounted.
