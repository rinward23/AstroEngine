# Developer Platform · Webhooks Submodule

- **Author**: Integration Reliability Team
- **Date**: 2024-05-27
- **Scope**: Submodule `developer_platform/webhooks` with channels `jobs` and `verification`. Describes webhook delivery mechanics for long-running jobs and HMAC verification helpers shared by SDKs and CLI workflows.

## Inputs

| Input | Location | Notes |
|-------|----------|-------|
| Webhook event schema | `schemas/webhooks/job_delivery.json` (to be generated) | Defines delivery payload structure aligned with OpenAPI components. |
| Solar Fire job datasets | `datasets/solarfire/jobs/*.json` | Provide real completed job records for regression testing. |
| Secrets management policy | `docs/governance/data_revision_policy.md` | Governs handling of webhook signing secrets. |

## Outputs

| Channel | Artefact |
|---------|----------|
| `jobs` | Long-running job webhook endpoints (`/webhooks/jobs/*`) documented in OpenAPI with retry expectations, delivery ordering, and Solar Fire dataset references. |
| `verification` | HMAC SHA-256 verification helpers in SDKs/CLI (`sdk.webhooks.verify_signature`, `astro webhooks verify`). |

## Delivery Semantics

- Deliveries include headers `X-Astro-Signature` (`t=<timestamp>, v1=<hex digest>`), `X-Astro-Delivery`, and `X-Astro-Event`.
- Retries follow exponential backoff with jitter (base 1s, cap 2m) and cease after 12 attempts. Receivers must return 2xx to acknowledge.
- Payload contains `job_id`, `event`, `attempt`, `status`, `result_url`, and dataset provenance (`solarfire_export_hash`, `ephemeris_cache_version`).
- Deliveries for the same `job_id` are ordered; receivers should use `attempt` for idempotency.
- Sandbox deliveries replay Solar Fire fixtures stored under `datasets/solarfire/jobs/` to guarantee deterministic demos.

## Verification Helpers

- Shared helper computes `expected = hmac_sha256(secret, f"{timestamp}.{payload}")` using constant-time comparison.
- Tolerated clock skew ±5 minutes; helpers fetch server time via `/status` endpoint when drift detected.
- SDK and CLI utilities expose explicit error types (`SignatureExpiredError`, `InvalidSignatureError`) inheriting from `ApiError` hierarchy.
- Secrets read from environment variables, keychain, or CLI `--secret-file` flag. Never logged or cached on disk.

## Testing

1. Contract tests using recorded webhook payloads from Solar Fire-derived job runs to ensure payload schema compatibility.
2. Replay harness `scripts/replay_webhook.py` verifying signature helper correctness against fixture secrets.
3. Load tests simulate 10k deliveries/hour using sandbox server to confirm retry backoff and idempotency logic.
4. Documentation smoke tests link webhook guides to actual dataset references.

## Acceptance Checklist

- [ ] Webhook schema aligned with OpenAPI components and committed under `schemas/`.
- [ ] Solar Fire job fixtures indexed and referenced in docs.
- [ ] SDK and CLI verification helpers share constant-time implementation with typed errors.
- [ ] Retry policy documented and enforced in integration tests.
- [ ] Governance artefacts updated with secret handling procedures.
