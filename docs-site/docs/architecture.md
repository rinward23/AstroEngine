# Architecture

!!! info "Specs referenced"
    - **SPEC-B-001** — Relationship data ingestion baseline
    - **SPEC-B-005** — Rulepack schema and gating DSL
    - **SPEC-B-013** — Rulepack DSL extensions
    - **SPEC-B-015** — Performance and caching envelope

The Relationship stack is layered to keep chart computation, rule evaluation, and report
assembly isolated yet composable.

1. **Ephemeris & Charting (Modules → Submodules)**

   - `astroengine.chart` produces natal and composite charts via the Swiss Ephemeris adapter.
   - `astroengine.synastry` orchestrates directional hits with domain tagging for downstream
     scoring.
   - Caching leans on Redis-backed stores with deterministic cache keys derived from
     body, timestamp, and configuration tuples (see [`ops/caching.md`](ops/caching.md)).

2. **Interpretation & Rulepacks (Channels → Subchannels)**

   - `core.interpret_plus` ingests YAML/JSON rulepacks defined by the schema in
     [`rulepacks/schema.md`](rulepacks/schema.md).
   - Rulepacks are versioned assets stored alongside notebooks, with golden checksums tracked
     in [`docs/fixtures/index.md`](fixtures/index.md).

3. **API Surfaces (B‑003, B‑006, B‑014, optional B‑012)**

   - FastAPI routers live under `astroengine.api.routers`. `scripts/build_openapi.py` materialises
     the OpenAPI documents and splits them by tag for the API section.
   - Each API page embeds a Redoc viewer, a Swagger link, Postman collection, and curl snippets.

4. **UI & Reporting**

   - Streamlit apps (`ui/streamlit`) implement the Relationship Lab, Report Builder, Rulepack
     Author, and Synastry Wheel experiences documented under the [UI Guides](ui/lab.md).
   - Report rendering templates are stored in `astroengine/narrative/templates` with PDF/Docx
     exporters described in [`cookbook/06_report_markdown.ipynb`](cookbook/06_report_markdown.ipynb)
     and [`cookbook/07_pdf_export.ipynb`](cookbook/07_pdf_export.ipynb).

![System overview](assets/diagrams/relationship-system.svg)

## Data Provenance & Integrity

* SolarFire exports must be converted to `csv` or `sqlite` datasets using `scripts/import_plus.py`.
* All sample data shipped with the docs is anonymised (rounded timestamps and truncated names).
* Golden outputs expose SHA-256 hashes; any drift triggers CI failures and blocks deployment.

## Ops Interfaces

* **docs-build** — Executes notebooks, runs mkdocs build, uploads artifact.
* **docs-deploy** — On `main`, deploys with `mike` and pushes to `gh-pages`.
* **link-check** — Uses `lychee` to ensure references remain valid.
