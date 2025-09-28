# Relationship caching and performance playbook

This guide documents the deterministic caching layer for the relationship stack
(synastry, composite, and Davison endpoints) and the guardrails we added for
latency tracking, profiling, and load testing.

## Cache architecture

* **Canonicalization** normalises request payloads: bodies are sorted by name,
  longitudes wrap into the `[0, 360)` range with 8 decimal precision, aspect
  lists are deduplicated, and policies are sorted recursively. The canonical
  payload hash (first 32 characters of a SHA-256 digest) is reused as the
  ETag/Redis key, guaranteeing deterministic memoization.【F:astroengine/cache/relationship/canonical.py†L13-L119】
* **Process cache**: a `cachetools.TTLCache` (default max 512 entries) holds the
  JSON-ready response body, status, and headers. It delivers microsecond hits
  for repeat requests on the same worker.【F:astroengine/cache/relationship/layer.py†L49-L110】
* **Redis cache**: optional when `REDIS_URL` is provided. Responses are stored as
  JSON or zstd-compressed blobs (prefix `J`/`Z`) with TTL defaults of 24 h
  (synastry) and 7 d (composite/Davison). Locks use `SET NX PX` with a
  configurable backoff to provide dogpile protection.【F:astroengine/cache/relationship/layer.py†L112-L193】
* **ETag support**: the ETag mirrors the canonical hash. Clients presenting
  `If-None-Match` receive a `304 Not Modified` shortcut and `X-Cache-Status:
  etag`.【F:app/routers/rel.py†L92-L150】

Process, Redis, and ETag layers are reported via Prometheus counters and the API
adds latency/payload histograms for observability.【F:app/routers/rel.py†L53-L89】

## Endpoint integration

Synastry/composite/Davison endpoints all flow through a shared helper that
handles cache lookups, single-flight compute, and response decoration. Payloads
are dumped to JSON once and reused across cache layers. Clients now see `ETag`
plus `X-Cache-Status` headers documenting hits versus recomputes.【F:app/routers/rel.py†L152-L237】

FastAPI tests cover the behaviour, including round-tripping ETags and verifying
`304` responses on warm cache hits.【F:tests/test_api_synastry_composites.py†L66-L97】

## Synastry memoization

Both the Plus-layer synastry module and the core engine now share a canonical
memoization key that includes positions, aspects, policies, weights, gamma, and
node-policy inputs. Results are cached as tuples for deterministic replay and
returned as fresh dict copies to avoid cross-request mutation. A public
`clear_synastry_memoization()` hook keeps tests and benchmarks reproducible.【F:core/rel_plus/synastry.py†L1-L102】【F:astroengine/core/rel_plus/synastry.py†L1-L104】

Unit tests confirm that repeated calls avoid recomputation and that cached
results remain isolated from caller-side mutation.【F:tests/test_synastry_memoization.py†L1-L33】

## Profiling snapshot

A `cProfile` run on a 13×13 synastry grid shows the matcher/orb policy helpers
as the dominant CPU hotspots (cumtime ~29 ms on the CI VM baseline). This keeps
focus on vectorising aspect matching before touching serialization layers.【fee20b†L1-L13】

## Load testing recipes

* **Locust**: `locust -f scripts/perf/locust_relationship.py --host=http://localhost:8000`
  mixes 70 % hot synastry payloads, 20 % variants, and 10 % Davison requests for
  cold coverage.【F:scripts/perf/locust_relationship.py†L1-L44】
* **k6**: `BASE_URL=http://localhost:8000 k6 run scripts/perf/k6_relationship.js`
  enforces the p50 < 60 ms / p95 < 150 ms targets under constant arrival with a
  cold-miss follow-up stage.【F:scripts/perf/k6_relationship.js†L1-L47】

## Benchmark gate

`pytest-benchmark` backs a golden baseline (`tests/perf/baseline_synastry.json`).
`tests/perf/test_relationship_perf.py` compares current mean/median timings
against the baseline with a 10 % allowance, ensuring CI flags regressions while
permitting small fluctuations.【F:tests/perf/test_relationship_perf.py†L1-L33】

Run `pytest tests/perf/test_relationship_perf.py` locally after substantial
synastry changes and update the baseline when the improvements are deliberate.
