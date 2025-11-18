# Exports & Interoperability Specification

- **Module**: `interop`
- **Maintainer**: Integration Guild
- **Last updated**: 2024-04-07
- **Source artifacts**:
  - `schemas/result_schema_v1.json`
  - `schemas/result_schema_v1_with_domains.json`
  - `schemas/contact_gate_schema_v2.json`
  - `schemas/natal_input_v1_ext.json`
  - `schemas/orbs_policy.json`
  - `schemas/export_manifest_v1.json`
  - `schemas/webhooks/job_delivery.json`
  - `docs/module/providers_and_frames.md` (provider cadence expectations referenced by transit exports)
  - Sample Solar Fire exports archived under `datasets/solarfire/*.sf`
  - Swiss Ephemeris kernels staged in `datasets/swisseph_stub/` (placeholder for production eph files)
  - Validation coverage: `tests/test_result_schema.py`, `tests/test_contact_gate_schema.py`, `tests/test_orbs_policy.py`

AstroEngine’s interoperability layer guarantees that every payload emitted from the runtime traces back to an auditable data
source—either a Solar Fire export, a Swiss Ephemeris calculation, or a user-supplied natal dataset. This document captures the
contracts governing JSON, tabular, SQLite, and calendar exports so downstream consumers can verify provenance without reverse
engineering implementation details. All field definitions below map to real measurements preserved in source archives; synthetic
values are expressly forbidden.

## Registry mapping

The schema registry currently exposes the following keys via `astroengine.data.schemas`:

- `interop.schemas.json_schema.result_v1`
- `interop.schemas.json_schema.result_v1_with_domains`
- `interop.schemas.json_schema.contact_gate_v2`
- `interop.schemas.json_schema.natal_input_v1_ext`
- `interop.schemas.json_schema.shadow_period_event_v1`
- `interop.schemas.json_schema.house_ingress_event_v1`
- `interop.schemas.json_schema.webhook_job_delivery_v1`
- `interop.schemas.json_data.orbs_policy`
- `interop.schemas.json_schema.export_manifest_v1`

These nodes ensure every export payload cites an audited schema or data document. New schemas MUST be registered alongside a
documented provenance trail before runtime code consumes them.

## AstroJSON schema family

AstroJSON is the canonical interchange format for AstroEngine. Each schema below is versioned independently to preserve backward
compatibility when observational datasets introduce new fields.

### `natal_v1`

Captures a single subject’s natal chart derived from Solar Fire (`*.sf`) exports or user-supplied data verified against Swiss
Ephemeris reproductions.

| Field | Type | Units / Format | Notes & Provenance |
| --- | --- | --- | --- |
| `profile_id` | string | slug | References the runtime profile (e.g., `profiles/base_profile.yaml#id`). |
| `subject.id` | string | UUID | Primary key mirroring `schemas/natal_input_v1_ext.json#/properties/subject_id`. |
| `subject.name` | string | UTF-8 | Pulled verbatim from Solar Fire export header `Name`. |
| `birth.timestamp` | string | ISO-8601 UTC | Converted from recorded timezone using Olson TZ from Solar Fire metadata. |
| `birth.location` | object | lat/long (decimal degrees), altitude (meters) | Verified against Solar Fire atlas coordinates; longitudes west are negative. |
| `coordinate_system` | string | enum (`tropical`, `sidereal`) | Values align with `natal_input_v1_ext.json#/properties/zodiac`. |
| `ayanamsha` | string | enum | Required when `coordinate_system="sidereal"`; must match Swiss Ephemeris constant names. |
| `house_system` | string | enum (Placidus, Whole Sign, …) | Mirrors Solar Fire export selection; see `natal_input_v1_ext.json`. |
| `bodies` | array<object> | | Each entry uses ephemeris longitudes measured in degrees from Solar Fire `.sf` lines validated through Swiss Ephemeris reproduction. |
| `bodies[*].id` | string | slug | Planet identifier (e.g., `sun`, `moon`, `ascendant`). |
| `bodies[*].longitude` | number | degrees (0–360) | Derived from export; cross-checked via Swiss Ephemeris `pyswisseph.calc_ut`. |
| `bodies[*].latitude` | number | degrees | Optional; included when Solar Fire provides declination/latitude columns. |
| `houses` | array<object> | | Ordered from I–XII; longitudes validated via provider parity checks. |
| `revision.provenance_uri` | string | URI | Points to signed export archive (e.g., `sf9://natal/2023-08-01-janedoe.sf`). |
| `revision.checksum` | string | SHA256 hex | Digest of the raw export file captured at import time. |

### `event_v1`

Represents a normalized event detected by the ruleset engine. Events MUST link back to the natal schema and include precise angle
measurements from Swiss Ephemeris data or Solar Fire validations.

| Field | Type | Units / Format | Notes & Provenance |
| --- | --- | --- | --- |
| `event_id` | string | UUID | Stable identifier recorded in SQLite export tables. |
| `subject_ref` | string | UUID | Matches `natal_v1.subject.id`. |
| `profile_id` | string | slug | Profile used to evaluate rulesets; aligns with CLI/API configuration. |
| `event_kind` | string | enum (`transit`, `ingress`, `station`, `lunation`, …) | Gate phrases documented in `docs/module/event-detectors/overview.md`. |
| `timestamp` | string | ISO-8601 UTC | Timestamp at peak or entry using Swiss Ephemeris interpolation; stored with millisecond precision. |
| `window` | object | start/end ISO-8601 UTC | Defines actionable window used by UI scheduling. |
| `geometry.aspect` | string | enum of aspect families | Values documented in `docs/module/core-transit-math.md` Aspect Canon. |
| `geometry.delta_longitude` | number | degrees | Signed Δλ computed from Swiss Ephemeris state vectors. |
| `geometry.orb` | number | degrees | Derived using policy in `docs/module/core-transit-math.md` (Orbs Matrix). |
| `severity.score` | number | dimensionless | Calculated per `docs/module/core-transit-math.md` Severity Model; stored with 3 decimal places. |
| `severity.band` | string | enum (`weak`, `moderate`, `strong`, `peak`) | Determined by severity thresholds. |
| `provenance.primary_uri` | string | URI | Points to Solar Fire window export or Swiss Ephemeris query bundle. |
| `provenance.validation_checksum` | string | SHA256 | Digest of JSON payload used for verification. |
| `ruleset.tag` | string | slug | Links to rule definition in `rulesets/` tree. |

### `transit_v1`

Tracks longitudinal/latitudinal samples for transiting bodies used to reconstruct events and severity scoring.

| Field | Type | Units / Format | Notes & Provenance |
| --- | --- | --- | --- |
| `series_id` | string | UUID | Groups samples for a scan window. |
| `subject_ref` | string | UUID | Matches natal subject (if personal) or `null` for mundane sweeps. |
| `provider_id` | string | enum (`swiss`, `skyfield`) | Declared provider; must match entries documented in `docs/module/providers_and_frames.md`. |
| `sample_cadence_minutes` | integer | minutes | Derived from provider cadence; see provider contract. |
| `bodies` | array<object> | | Sorted by timestamp. |
| `bodies[*].id` | string | slug | Body name per module registry. |
| `bodies[*].samples` | array<object> | | Monotonic time series. |
| `bodies[*].samples[*].timestamp` | string | ISO-8601 UTC | Rounded to nearest second; captured from Swiss Ephemeris `swe_calc_ut`. |
| `bodies[*].samples[*].longitude` | number | degrees | Real output from provider call (no smoothing). |
| `bodies[*].samples[*].latitude` | number | degrees | Optional; included for declination-sensitive detectors. |
| `bodies[*].samples[*].speed_longitude` | number | degrees/day | Derived from adjacent samples; ensure Δλ continuity across 0°/360°. |
| `provenance.scan_window` | object | start/end ISO-8601 UTC | The requested time range. |
| `provenance.ephemeris_checksum` | string | SHA256 | Digest of Swiss Ephemeris or Skyfield kernel bundle used. |

### `webhook_job_delivery_v1`

Webhook deliveries reference the asynchronous jobs API used by the developer platform. Payloads follow `schemas/webhooks/job_delivery.json` and embed explicit provenance for Solar Fire exports and Swiss Ephemeris caches.

| Field | Type | Notes |
| --- | --- | --- |
| `schema.id` | string | Constant `astroengine.webhooks.job_delivery`. |
| `job_id` | string | Unique identifier echoed by `/webhooks/jobs/*` endpoints. |
| `event` | string | Enumerated lifecycle marker (`job.accepted`, `job.processing`, `job.retry`, `job.completed`, `job.failed`). |
| `status` | string | Operational state (`queued`, `running`, `succeeded`, `failed`, `cancelled`). |
| `attempt` | integer | Retry counter (bounded to 12 attempts per policy). |
| `result_url` | string | HTTPS URL referencing the JSON/ZIP result artefact. |
| `window.start` / `window.end` | string | ISO-8601 timestamps summarising the scan horizon tied to the job. |
| `context.profile_id` | string | Profile configured for the run; maps to `profiles/*.yaml`. |
| `provenance.solarfire_export_hash` | string | SHA256 digest of the Solar Fire export archived under `datasets/solarfire/jobs/`. |
| `provenance.ephemeris_cache_version` | string | Identifier for the Swiss Ephemeris cache (e.g., `swisseph-2.10.03`). |

### Detector payload schemas

Detectors that emit standalone event payloads expose dedicated JSON Schema documents to keep the data contracts auditable; see
the [`event-detectors` overview](event-detectors/overview.md#schema-alignment) for runtime context. Sample payloads in
`tests/test_result_schema.py` validate each schema so the docs, registry, and runtime stay aligned:

- `shadow_period_event_v1` (`schemas/shadow_period_event_v1.json`): captures `astroengine.events.ShadowPeriod` windows produced by the stations shadow detector, including paired station metadata and longitudinal bounds.
- `house_ingress_event_v1` (`schemas/house_ingress_event_v1.json`): normalises `astroengine.events.IngressEvent` payloads emitted by the house ingress detector, covering motion flags, longitudinal speeds, and house labels.

## CSV & Parquet exports

AstroEngine produces two tabular families mirroring the JSON schemas above. All CSV files are UTF-8 with Unix line endings;
Parquet files use Snappy compression.

### `transit_events.csv` / `transit_events.parquet`

- **Partitioning**: `year=YYYY/month=MM` based on `timestamp`.
- **Columns**:
  - `event_id` (STRING)
  - `subject_ref` (STRING)
  - `profile_id` (STRING)
  - `event_kind` (STRING)
  - `aspect` (STRING)
  - `orb_deg` (DOUBLE)
  - `severity_score` (DOUBLE)
  - `severity_band` (STRING)
  - `timestamp_utc` (TIMESTAMP)
  - `window_start_utc` (TIMESTAMP)
  - `window_end_utc` (TIMESTAMP)
  - `provenance_uri` (STRING)
  - `ruleset_tag` (STRING)

### `transit_tracks.csv` / `transit_tracks.parquet`

- **Partitioning**: `provider_id` / `year` / `month` to keep provider parity comparisons efficient.
- **Columns**:
  - `series_id` (STRING)
  - `provider_id` (STRING)
  - `body` (STRING)
  - `timestamp_utc` (TIMESTAMP)
  - `longitude_deg` (DOUBLE)
  - `latitude_deg` (DOUBLE, nullable)
  - `speed_longitude_deg_per_day` (DOUBLE)
  - `scan_window_start_utc` (TIMESTAMP)
  - `scan_window_end_utc` (TIMESTAMP)
  - `ephemeris_checksum` (STRING)

Writers MUST maintain deterministic column ordering and include a header row in CSV outputs. When converting to Parquet, use
logical types (`TIMESTAMP_MILLIS`) to preserve millisecond precision, matching Solar Fire’s export granularity.

## SQLite schema (`transits_events` database)

The CLI may persist results to SQLite for local inspection. The database file stores a single logical dataset with supporting
indexes to accelerate event lookups.

```sql
CREATE TABLE transits_events (
    event_id TEXT PRIMARY KEY,
    subject_ref TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    aspect TEXT,
    orb_deg REAL,
    severity_score REAL NOT NULL,
    severity_band TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    window_start_utc TEXT NOT NULL,
    window_end_utc TEXT NOT NULL,
    provenance_uri TEXT NOT NULL,
    ruleset_tag TEXT NOT NULL,
    validation_checksum TEXT NOT NULL
);

CREATE INDEX idx_transits_events_subject_time
    ON transits_events (subject_ref, timestamp_utc);
CREATE INDEX idx_transits_events_kind_band
    ON transits_events (event_kind, severity_band);
```

Timestamps are stored as ISO-8601 strings to avoid timezone drift; consumers should parse them with timezone-aware libraries.
`validation_checksum` stores the SHA256 digest of the serialized `event_v1` payload so SQLite queries remain tied to the JSON
exports.

## ICS event format

Calendar exports translate each `event_v1` payload into a deterministic VEVENT block. The runtime emits RFC 5545 compliant
records with the following fields:

- `UID`: `<event_id>@astroengine.io`.
- `DTSTAMP`: Generation timestamp in UTC.
- `DTSTART`: `timestamp_utc` converted to the subscriber’s preferred timezone; defaults to UTC if unspecified.
- `DTEND`: `window_end_utc` projected into the same timezone; if the event is instantaneous, use `DTSTART` + 5 minutes.
- `SUMMARY`: `"{event_kind|title} – {ruleset_tag}"` (e.g., `"Mars Square Natal Sun – vitality_checks"`).
- `DESCRIPTION`: Multiline text summarizing severity band, orb, aspect geometry, and provenance URI. Include Solar Fire reference
  identifiers so analysts can cross-check the original export.
- `CATEGORIES`: Severity band (capitalized) and channel/subchannel path (e.g., `Transit/Natal`).
- `URL`: Direct link to the API result if available; otherwise omit.
- `X-ASTROENGINE-PROVENANCE`: Proprietary extension that repeats `provenance_uri` and `validation_checksum` for calendar clients
  that archive metadata.

ICS payloads must never downsample or average the underlying event timing. All date conversions rely on the Olson timezone from
the natal record, ensuring daylight-saving transitions mirror Solar Fire’s documented offsets.

## Export manifests

All tabular/calendar exports now emit a sidecar manifest (`<file>.manifest.json`) that adheres to `schemas/export_manifest_v1.json`. The payload captures:

- `profile_ids`: unique profiles observed in the exported events (falls back to CLI `--profile` when events omit metadata).
- `natal_ids`: deduplicated natal references surfaced during canonicalization.
- `scan_window`: explicit CLI window when available, otherwise the earliest/latest event window detected in metadata.
- `outputs[*]`: checksum and size metadata for each artifact. Directory exports (e.g., Parquet datasets) include per-file hashes alongside an aggregate checksum so auditors can diff incremental refreshes.
- `meta`: contextual arguments (provider, detectors, calendar title, etc.) plus the total number of canonical events captured.

CLI commands producing SQLite/Parquet/ICS exports write the manifest next to the generated file or dataset directory. Integrators should archive both the dataset and manifest to preserve the verification trail.

## Provenance & validation requirements

- Every export references a concrete dataset URI. Solar Fire archives should be stored under `datasets/solarfire/` with SHA256
  digests logged in `docs/governance/data_revision_policy.md`.
- Ephemeris computations must log the Swiss Ephemeris or Skyfield kernel path plus checksum. When using the Swiss stub during
  development, document that the data is truncated and unsuitable for production severity scoring.
- Validation suites (`tests/test_result_schema.py`, etc.) MUST load at least one golden payload per schema, recompute the
  `validation_checksum`, and compare against recorded expectations.
- CLI commands emitting CSV/Parquet/SQLite/ICS files append a manifest JSON alongside each export summarizing profile IDs,
  scan windows, and checksums. Consumers should validate against `schemas/export_manifest_v1.json`.
- If a downstream integration cannot resolve the recorded URI, the export is considered non-compliant; retry logic must fetch the
  missing dataset instead of substituting synthetic data.

## Extending interoperability

When introducing new exports:

1. Add the schema or data file under `schemas/` with accompanying provenance notes.
2. Register the schema via `astroengine.data.schemas` and document it in the appropriate section above.
3. Add pytest coverage that exercises the new payload end-to-end, including checksum verification against Solar Fire or Swiss
   Ephemeris reproductions.
4. Update `docs/burndown.md` and the governance revision log to capture the new deliverable.
5. Ensure the dataset index (CSV/Parquet/SQLite) maintains compatibility with the module → submodule → channel → subchannel
   hierarchy; never drop columns without a migration plan.

Maintaining this specification keeps AstroEngine’s exports demonstrably linked to real observational data, protecting both the
runtime’s integrity and downstream consumers.
