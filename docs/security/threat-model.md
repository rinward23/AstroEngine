# AstroEngine Threat Model

## Assets

- Astrology datasets imported from SolarFire CSV/SQLite exports.
- Real-time ephemeris cache containing planetary positions.
- Tenant-specific natal charts and generated reports.

## Trust Boundaries

1. Public internet → Ingress/WAF.
2. Ingress → API namespace (FastAPI, workers, Streamlit).
3. API namespace → Data namespace (PostgreSQL HA, Redis, object storage).
4. CI/CD pipeline → Kubernetes cluster (Helmfile deployer).

## Threats & Mitigations

| Threat | Mitigation |
| --- | --- |
| Credential theft via CI | Short-lived workload identity, Cosign signing, Terraform remote state with backend encryption. |
| SQL injection | Parametrized queries, SQLAlchemy ORM, automated tests in `ops/pipelines/github-actions.yaml`. |
| Data exfiltration | Row-level security on charts, tenant quotas enforced at API, audit logging of exports. |
| Cache poisoning | Strict authentication for Redis, TLS enforced, secrets rotated via Vault. |
| Supply chain attacks | SBOM validation, Cosign signature verification in admission controller, `no-latest-tags` policy. |

## Data Protection

- All data at rest encrypted using provider-managed keys.
- Secrets pulled from Vault using short-lived tokens; no plaintext secrets stored in Git.
- Backups written to object storage with lifecycle transitions to cold storage after 90 days.
