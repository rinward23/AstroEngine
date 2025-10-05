# AstroEngine performance success metrics

These success metrics define the target operating envelope for high-traffic AstroEngine services. Each metric ties back to concrete telemetry that is already emitted by the platform so operators can validate improvements against live data.

## P95 API latency on popular endpoints
- **Target:** Reduce by 30–50% relative to the current baseline.
- **Scope:** FastAPI routers that back the relationship, mundane, and synastry APIs.
- **Measurement:** Track the `api_request_latency_ms` histogram (P95) exposed through Prometheus and visualized on the `Optimizer Latency` Grafana dashboard. Compare the 30-day rolling median to the pre-optimization baseline captured in `observability/dashboards/optimizer_latency.json`.
- **Data requirements:** Use the production Prometheus time series with request tags (`endpoint`, `profile`) sourced from live traffic. Synthetic load is acceptable only when replaying real request logs through the `scripts/perf` harness.

## Cache hit rate for warmed day ranges
- **Target:** Maintain cache hit ratio above 85% for the day-range queries highlighted in `docs/performance/relationship_caching.md`.
- **Scope:** Redis-backed relationship cache and per-process memoization for synastry/composite/Davison computations.
- **Measurement:** Monitor the `cache_hit_ratio` gauge and `cache_hits_total`/`cache_misses_total` counters emitted by `astroengine.cache.relationship.layer`. Dashboards in `observability/dashboards/returns_perf.json` provide the hit-rate panel for warmed ranges. Audit warmed cache windows daily using real Solar Fire ingestion logs.
- **Data requirements:** Inputs come from the Redis telemetry stream and persisted Solar Fire CSV imports that seed warmed caches. Do not model or extrapolate beyond recorded traffic windows.

## Cold start to first response
- **Target:** <500 ms from worker startup to first successful API response when running under `uvloop` and `httptools`.
- **Scope:** Deployment scenarios that scale-to-zero or recycle worker pods.
- **Measurement:** Instrument the boot sequence using `startup_duration_ms` timers captured in Prometheus and log spans annotated with `server.startup`. Cross-check against the load-test harness in `scripts/perf/k6_relationship.js` which issues a cold request immediately after startup.
- **Data requirements:** Use deploy logs and the Prometheus startup timer derived from production rollouts. Corroborate with captured k6 traces using real request payloads.

## CI duration and fail-fast policy
- **Target:** Keep GitHub Actions `ci.yml` jobs under 6 minutes with fail-fast behaviour for compile/lint stages.
- **Scope:** All steps invoked by `make fullcheck` and `python -m astroengine.maint --full --strict`.
- **Measurement:** Review the `ci_duration_seconds` metric emitted by the workflow collector and stored in the build analytics database. Ensure lint/compile steps use the `continue-on-error: false` policy so regressions abort immediately.
- **Data requirements:** Rely on actual GitHub Actions run metadata mirrored into the CI SQLite store referenced in `docs/QUALITY_GATE.md`. Do not extrapolate from local timings.

## Zero downgrade failures across SQLite and Postgres
- **Target:** Zero downgrade failures when running alembic migrations against both SQLite (development) and Postgres (staging/production).
- **Scope:** Every migration in `migrations/` and database initialization routines under `astroengine/db`.
- **Measurement:** Execute `alembic downgrade` smoke tests in CI for both backends, confirming matching schema states. Monitor the `db_migration_failures_total` counter to ensure it remains at zero.
- **Data requirements:** Use real migration histories from the database fixtures and captured schema dumps. Any observed failure requires a verified reproduction script tied to actual database states.
