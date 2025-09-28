---
title: Relationship Stack Overview
hide:
  - navigation
  - toc
---
<meta name="doc-version" content="v0.1" />

# Relationship Stack B‑001 → B‑015

!!! info "Spec lineage"
    This site consolidates the developer and analyst guidance for the Relationship stack
    spanning **SPEC-B-001** through **SPEC-B-015**. Each section links back to its
    originating specification and includes reproducible examples with golden outputs.

The Relationship stack transforms natal datasets sourced from SolarFire exports into
repeatable, data-backed relationship analyses. The platform embraces the
**module → submodule → channel → subchannel** hierarchy defined in the AstroEngine core
packages, ensuring that expansions never replace or silently remove existing modules.

<div class="grid cards" markdown>

-   :material-rocket-launch: __Quickstart__ — [Provision the toolchain](quickstart.md) and complete a
    10-minute end-to-end walkthrough.
-   :material-book-open-page-variant: __Cookbook__ — Execute the nine version-pinned
    notebooks that cover the B-stack journey from **Birth data → PDF**.
-   :material-api: __API Reference__ — [OpenAPI-derived docs](api/relationship.md)
    for B‑003, B‑006, B‑012, and B‑014 endpoints with Postman collections and curl snippets.
-   :material-script-text: __Rulepacks__ — Browse the schema and DSL from B‑005 and B‑013,
    plus annotated examples ready for analysts to customise.
-   :material-monitor-dashboard: __UI Guides__ — Operational handbooks for the Lab, Report Builder,
    Rulepack Author, and Synastry Wheel interfaces.
-   :material-server-network: __Ops Runbook__ — Deployment, caching, and licensing procedures with
    golden notebook checksums that enforce deterministic outputs.

</div>

![Relationship stack data flow](assets/diagrams/relationship-system.svg)

## Versioning & CI

All documentation lives alongside the AstroEngine source tree. Releases are published with
[`mike`](https://github.com/jimporter/mike) and deployed by the `docs-deploy` GitHub Actions
workflow. Notebook execution and golden-output validation occur in the `docs-build` job on
every push. The currently published version is **v0.1** with `latest` tracking `main`.

## Golden Outputs & Provenance

Every notebook ships with a `Results checksum` cell. Checksums are generated from
real ephemeris-backed computations using the bundled Swiss Ephemeris stub datasets. The
fixtures live under [`docs/fixtures/`](fixtures/index.md) and are regenerated via the
`scripts/build_openapi.py` and `scripts/exec_notebooks.py` utilities.

## Getting Help

* Engineering: `#astroengine-rel` Slack channel.
* Analyst enablement: `rel-onboarding@astroengine.dev`.
* Architecture & security reviews: [go/astro-arch](https://astroengine.dev/architecture).
