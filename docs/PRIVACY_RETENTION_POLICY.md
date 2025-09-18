<!-- >>> AUTO-GEN BEGIN: Privacy & Retention v1.0 (instructions) -->
PII
- Prefer pseudonymous IDs; names optional; redact PII in exports by default; consent flags for shared datasets.

Retention
- Default retention 90 days for raw inputs; derived exports kept indefinitely with PII stripped.
- Right to deletion: implement purge by `natal_id` and snapshot hash.

Security
- No secrets in repo; OIDC for releases; audit third‑party licenses.

Acceptance
- Dry‑run purge logs what would be removed; actual purge removes snapshots and exports by ID.
<!-- >>> AUTO-GEN END: Privacy & Retention v1.0 (instructions) -->
