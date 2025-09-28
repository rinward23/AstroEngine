# Relationship Suite Release Roll-Up (v0.1.0)

This roll-up consolidates the readiness activities for the Relationship Suite modules (B-001 → B-016) as we target the `v0.1.0` minimum viable product. The plan follows the repository's module → submodule → channel → subchannel layout to prevent accidental removal of critical components and to keep every deliverable tied to verifiable datasets (Solar Fire exports, CSV archives, SQLite stores, and related fixtures).

## 1. Scope & Version Map

| Module | Artifact | Version |
| --- | --- | --- |
| B-001 Core (Composite/Davison Math) | `relation-core` (Py) | 0.1.0 |
| B-002 Synastry Engine | `synastry-core` (Py) | 0.1.0 |
| B-003 Relationship API | `relationship-api` (Docker `api-rel`) | 0.1.0 |
| B-004 Streamlit Lab | `relationship-lab` (Streamlit app) | 0.1.0 |
| B-005 Interpret Core | `interpret-core` (Py) | 0.1.0 |
| B-006 Interpret API | `interpret-api` (Docker `api-int`) | 0.1.0 |
| B-007 Report Builder (Streamlit) | `report-builder` | 0.1.0 |
| B-008 Rulepack Authoring UI | `rulepack-ui` (Next.js) | 0.1.0 |
| B-009 Synastry Wheel (React) | `synastry-wheel` (npm pkg) | 0.1.0 |
| B-010 Houses (Comp/Dav) | `houses` (Py subpkg) | 0.1.0 |
| B-011 Midpoints Scanner | `synastry-midpoints` (Py) | 0.1.0 |
| B-012 Timelines | `relation-timeline` (Py) | 0.1.0 |
| B-014 Report Export | `report-service` (Docker `api-report`) | 0.1.0 |
| B-015 Caching/Perf | infra changes | – |
| B-016 Docs | `docs-site` (MkDocs) | 0.1.0 |
| B-013 Packs | `interpret-packs` (YAML bundle) | 0.1.0 |

All artifacts must retain their backing datasets; none of the modules listed above can be pruned during stabilization. When large Solar Fire or CSV exports are updated, index regeneration scripts should be run so that downstream channels always resolve the latest data without synthetic placeholders.

## 2. Branching & Freeze

- **Branches:** `main` remains active. Cut `release/0.1` for stabilization; tag each repository with `v0.1.0` once sign-off is complete.
- **Freeze:** Occurs at T-5 days. Afterward only P0/P1 fixes enter `release/0.1`, keeping datasets and schemas intact.

## 3. System-Wide Readiness Gates

- **Functional:** SPEC acceptance criteria across B-001 through B-016 must pass continuous integration.
- **Determinism:** Golden fixtures remain stable. Only well-documented floating-point tolerances are acceptable.
- **Performance:** Ensure p50/p95 budgets are met for B-002, B-003, B-012, and B-015.
- **Security:** Software composition and secrets scanning must be clean; CORS allowlists set.
- **Licensing:** Swiss Ephemeris location configured and license notice present in documentation.

## 4. Pre-Release Checklists

### Code & Tests

- Unit coverage ≥ 85% across core engines.
- Property tests (angles, severity) pass using real Solar Fire-derived fixtures.
- API contract tests remain aligned with OpenAPI snapshots.

### Build & Packaging

- Python wheels/sdists built on Python 3.11 with pinned dependencies.
- Docker images for `api-rel`, `api-int`, `api-report` generated with SBOM metadata.
- npm build for `synastry-wheel` includes up-to-date type definitions.

### Data & Fixtures

- Golden fixtures refreshed with provenance metadata; regenerate checksums.
- Ship anonymized sample datasets; document any transformations so users can re-index as needed.

### Docs & UIs

- MkDocs site builds and deploys to staging with executed notebooks.
- Smoke flows succeed for Relationship Lab, Report Builder, and Rulepack UI, ensuring their channels consume live data streams.

### Ops

- Redis deployed with persistence; namespace keys `syn|comp|dav|mid|tl`.
- Observability dashboards expose latency, cache hit rate, and error metrics.
- Rate limits configured; confirm CORS allowlist against deployment plan.

## 5. Release Train (T-7 → T+2)

- **T-7:** Cut `release/0.1`; freeze features; initiate RC builds.
- **T-6:** Deploy RC1 to staging for all services. Run E2E and load tests against real datasets.
- **T-5:** Enforce code freeze. Accept only P0/P1 fixes; lock documentation.
- **T-3:** Produce RC2 if necessary and hold sign-off (Go/No-Go).
- **T-0:** Execute blue/green rollout:
  1. Deploy `api-int`; validate health/liveness.
  2. Deploy `api-rel`; verify `/healthz` and smoke flows.
  3. Deploy `api-report`; run PDF export smoke.
  4. Flip Relationship Suite UIs to new API base URLs.
- **T+1:** Monitor p95, error rates, and cache hits; triage anomalies.
- **T+2:** Tag `v0.1.0`; publish release notes and point docs alias `latest` to the new build.

## 6. Rollback & Backout

- Maintain blue/green deployments with previous images (`:v0.1.0-rcN`, `:prev`).
- Rollback order: UIs → `api-report` → `api-rel` → `api-int`.
- Capture rulepack store snapshots before deploy; restore snapshot on rollback.

## 7. Post-Release Actions

- Collect adoption metrics, cache hit ratios (≥ 0.75 target), and latency dashboards.
- Open `v0.1.1` milestone; triage P2+ issues.
- Schedule pack updates (B-013) and house rules calibration (B-010) for `v0.1.1`.

## 8. Ownership Matrix

| Area | Owner | Backup |
| --- | --- | --- |
| Core engines (B-001/2/10/11/12) | Eng-Core | Eng-Algo |
| APIs (B-003/6/14) | Eng-API | Eng-Ops |
| UIs (B-004/7/8/9) | Eng-UI | Eng-API |
| Caching/Perf (B-015) | Eng-Ops | Eng-Core |
| Docs (B-016) | Tech-Writer | Eng-Core |

## 9. Environment & Config Cheatsheet

- APIs: `REDIS_URL`, `RATE_LIMITS`, `CORS_ALLOW_ORIGINS`, `EPHEMERIS`, `CACHE_TTL_*`, `API_KEYS` (when applicable).
- Report service: Ensure Chromium or WeasyPrint fallback with required fonts and resource limits.
- Docs CI: Provide Swiss ephemeris path; skip long notebooks via flag when necessary.

## 10. Release Notes Template

- Highlights and breaking changes (none expected for 0.1.0).
- API additions and performance updates.
- Known issues and upgrade notes with references to verified datasets.

---

Keep this roll-up under version control so that future module or dataset additions can extend the plan without risking loss of existing modules or data integrity.
