# Solar Fire Job Replay Fixtures

These JSON payloads were captured from sandbox deliveries that replayed
completed Solar Fire runs. Each record mirrors the webhook payloads
published by the `/webhooks/jobs/*` endpoints and references the Solar
Fire export or Swiss Ephemeris cache used by the underlying run. Hashes
are truncated copies of the signed manifests recorded in
`docs/governance/data_revision_policy.md`.

| File | Description |
|------|-------------|
| `job_delivery_completed.json` | Completed relationship scan seeded with Solar Fire export `sf9://jobs/2024-05-12-relationship.sf`. |
| `job_delivery_failed.json` | Failed retry example referencing Solar Fire export `sf9://jobs/2024-05-13-relationship.sf`. |
