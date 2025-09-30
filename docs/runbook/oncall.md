# AstroEngine On-Call Runbook

## Quick Links

- PagerDuty: https://pagerduty.com/astroengine
- Grafana Dashboards: https://grafana.astroengine.com
- Incident Doc Template: https://docs.astroengine.com/incidents/template

## Triage Checklist

1. **Acknowledge alert** within 5 minutes.
2. **Identify blast radius** using Grafana dashboards `Engine Scan Throughput` and `Database Health`.
3. **Check recent deploys** via GitHub Actions; if a production deploy occurred within the last hour, initiate automatic rollback by running `helmfile --environment prod destroy --selector name=api`.
4. **Communicate status** in #ops-incident every 15 minutes.

## Common Scenarios

### Elevated Latency

- Inspect Optimizer Latency dashboard to confirm P95 spikes.
- Flush Redis cluster by running `redis-cli --cluster check` to identify slot imbalance.
- If cache miss rate exceeds 20%, scale worker pool using `kubectl scale deployment/astroengine-workers --replicas=desired`.

### Database Failover

- Use `psql` against the replica endpoint to confirm replication lag < 5s.
- Trigger failover by promoting replica via cloud provider console when the primary is unhealthy for > 2 minutes.
- Restore PITR snapshot using `terraform apply -target=module.database` after confirming backup recency.

## Post-Incident

- File retrospective within 48 hours including root cause and prevention tasks.
- Review alert thresholds and update `observability/otel/collector-config.yaml` if new signals are required.
