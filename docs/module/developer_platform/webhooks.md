# Developer Platform · Webhooks Submodule

- **Author**: Integration Reliability Team
- **Date**: 2024-05-27
- **Scope**: Submodule `developer_platform/webhooks` with channels `jobs` and `verification`. Describes webhook delivery mechanics for long-running jobs and HMAC verification helpers shared by SDKs and CLI workflows.

## Inputs

| Input | Location | Notes |
|-------|----------|-------|
| Webhook event schema | `schemas/webhooks/job_delivery.json` | Draft 2020-12 schema registered via `astroengine.data.schemas` for `/webhooks/jobs/*`. |
| Solar Fire job datasets | `datasets/solarfire/jobs/*.json` | Recorded deliveries replayed during contract tests and CLI verification. |
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

## Jobs Channel

- JSON payloads follow `schemas/webhooks/job_delivery.json` and are validated at runtime via `astroengine.validation.validate_payload("webhook_job_delivery_v1", payload)`.
- Fixtures under `datasets/solarfire/jobs/job_delivery_*.json` mirror recorded deliveries so contract tests and docs can cite concrete data sources.
- Each payload references the originating Solar Fire export (`sf9://` URI plus SHA256 hash) and Swiss Ephemeris cache version, ensuring downstream systems can audit provenance.

## Verification Channel

- SDK/CLI consumers rely on `astroengine.developer_platform.webhooks.verify_signature` plus the `astro webhooks verify` helper to reproduce the `X-Astro-Signature` calculation (`expected = HMAC_SHA256(secret, f"{timestamp}.{payload}")`).
- Failures raise typed errors (`SignatureExpiredError`, `InvalidSignatureError`) that map directly to docs and OpenAPI error codes.
- The CLI command accepts payload/secret files and header values so operators can validate deliveries captured from observability tooling without writing custom scripts.

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

- [x] `schemas/webhooks/job_delivery.json` registered as `webhook_job_delivery_v1` and covered by `tests/test_webhook_job_contracts.py`.
- [x] Solar Fire job fixtures stored under `datasets/solarfire/jobs/` and cited throughout this document and tests.
- [x] SDK (`astroengine.developer_platform.webhooks`) and CLI (`astro webhooks verify`) helpers reuse the same constant-time verification primitives.
- [ ] Retry policy remains documented above; integration tests to assert retry scheduling are still pending.
- [ ] Governance artefacts (`docs/governance/data_revision_policy.md`) still require a signing-secret appendix for production rollout.
