# Caching & Performance (SPEC-B-015)

Caching is layered across the relationship stack to keep synastry and transit scans responsive.

## Strategy

* **Notebook fixtures** — `caching_metrics.json` captures cold vs warm timings to flag regressions.
* **Redis** — Keys follow `{channel}:{hash(bodies+targets+orb)}` to avoid accidental collisions.
* **ETag support** — API responses include deterministic hashes so clients can issue conditional
  requests and receive `304 Not Modified`.

## Instrumentation

* `astroengine.core.transit_engine.TransitEngine` exposes `cache_samples` for warm caches.
* `/v1/scan/*` endpoints emit `X-Cache` headers recorded by `docs-build`.

See [`cookbook/09_caching_perf.ipynb`](../cookbook/09_caching_perf.ipynb) for an end-to-end example.
