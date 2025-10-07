# Developer Platform Module Overview

- **Author**: AstroEngine Developer Experience Working Group
- **Date**: 2024-05-27
- **Scope**: Module → submodule → channel hierarchy covering SDKs, CLI tooling, and the Developer Portal that operationalises the SPEC-17 requirements without removing or renaming existing runtime modules.

The developer platform module guarantees that external integrations are driven by the frozen OpenAPI specifications published under `openapi/` and that all runtime outputs are derived from verified Solar Fire exports, Swiss Ephemeris datasets, or database artefacts versioned in `datasets/`. Each submodule below inherits the following invariants:

## Registry mapping

- `developer_platform.sdks.languages.{typescript,python}`
- `developer_platform.agents.toolkits.python`
- `developer_platform.cli.workflows.transit_scan`
- `developer_platform.devportal.surfaces.{docs,playground,collections}`
- `developer_platform.webhooks.contracts.{jobs,verification}`
- `developer_platform.installers.windows.one_click`

The registry entries currently mark these surfaces as planned deliverables while anchoring them to the documentation listed in this file.

1. **Source-of-truth alignment** – All generated artefacts originate from the `openapi/v*.json` schema files. Any hand-edit passes must log a provenance note referencing the schema hash and the Solar Fire or Swiss Ephemeris datasets used for validation.
2. **Hierarchical integrity** – Submodules may extend the hierarchy with new channels/subchannels but must not delete or orphan existing modules. Regression tests confirm that registry entries in `astroengine/modules` still resolve.
3. **Data fidelity** – SDK and CLI outputs surface only values produced by sanctioned providers (Swiss Ephemeris cache, natal chart datasets in `datasets/solarfire/`, or SQLite bundles shipped under `datasets/sqlite/`). Synthetic ephemerides or placeholder natal data are disallowed.
4. **Observability** – Every client includes structured logging hooks that reproduce the identifiers specified in `docs/module/interop.md` (profile IDs, ruleset tags, provider names) so downstream audit trails can be reconstructed from production telemetry.

The remainder of this document routes readers to the submodule specifications and records cross-cutting requirements.

## Submodules

| Submodule | Channel | Description |
|-----------|---------|-------------|
| `sdks` | `typescript`, `python` | Typed SDKs generated from OpenAPI with ergonomic wrappers, retries, pagination, streaming, and typed errors. |
| `agents` | `python` | Agent automation toolkit exposing registry discovery, scan orchestration, and dataset-backed context summaries. |
| `cli` | `workflows` | Python-based CLI commands aligned with runtime modules (`scan`, `events`, `election`, `progressions`, `returns`, `export`). |
| `devportal` | `docs`, `playground`, `collections` | Developer portal assets (Docusaurus site, runnable playground, Postman/Insomnia collections). |
| `webhooks` | `jobs`, `verification` | Optional webhook delivery contracts and signature verification helpers. |
| `installers` | `windows` | Desktop installer experiences, beginning with the SPEC-02 Windows one-click workflow. |

Each submodule document contains:

- Inputs (schemas, datasets, configuration files) with checksums when available.
- Outputs (packages, CLIs, static sites) plus publishing channels (PyPI, npm, GitHub Pages).
- Idempotency, retry, pagination, and streaming strategies.
- Error taxonomy mapped to `docs/module/ruleset_dsl.md` and runtime severity classifications.
- Acceptance checkpoints tied to automated contract tests and Solar Fire cross-check datasets.

## Release & Versioning Flow

1. Freeze `/openapi.json` from the FastAPI service into `openapi/v{major}.{minor}.json` prior to any client release.
2. Run SDK generators (`sdks/typescript/scripts/generate.ts`, `sdks/python/scripts/generate.py`) with the frozen schema. Store generator manifests capturing schema hash, commit SHA, and dataset checksum references.
3. Execute contract tests against the Prism mock derived from the same schema and compare sampled responses to Solar Fire or Swiss Ephemeris baselines stored under `generated/`.
4. Publish SDKs using Semantic Versioning aligned with API major versions. Record release metadata in `docs/governance/data_revision_policy.md` alongside dataset index updates.
5. Deploy the Developer Portal with a changelog entry referencing the schema version and Solar Fire comparison fixtures used in the playground.

## Dependencies & Observability

- **Transport libraries**: `undici`/`fetch` (TypeScript), `httpx` + `tenacity` (Python), both configured for TLS ≥1.2.
- **Logging**: Clients emit structured logs containing `request_id`, `idempotency_key`, `profile_id`, and dataset identifiers such as Solar Fire export hashes.
- **Metrics**: Retries increment `astroengine.sdk.retry_count` (tagged by endpoint) and CLI workflows emit `astroengine.cli.job_duration_seconds`.
- **Security**: API keys sourced from OS keychains or environment variables; OIDC tokens cached in memory with automatic refresh using the discovery document recorded in `datasets/oidc/metadata.json`.

Refer to the submodule documents in `docs/module/developer_platform/` for implementation-grade directives.
