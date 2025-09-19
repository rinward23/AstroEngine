<!-- >>> AUTO-GEN BEGIN: Observability v1.0 (instructions) -->
Logging:
- JSON logs; levels TRACE..ERROR; include request_id, provider, profile, ruleset_tag.
- Event counters per module; refine iterations; cache hits/misses.

Metrics:
- Prometheus text or statsd: scan_duration_ms, events_emitted, events_refined, severity_mean, cache_hit_ratio.

CLI flags:
- --log-level, --metrics-exporter, --metrics-path.
Acceptance: metrics increment appropriately in integration test.
<!-- >>> AUTO-GEN END: Observability v1.0 (instructions) -->
