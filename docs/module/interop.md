# Exports & Interoperability Specification

- **Module**: `interop`
- **Author**: AstroEngine Integration Guild
- **Date**: 2024-05-27
- **Source datasets**: AstroJSON schemas (`schemas/astrojson/*.json`), Solar Fire export samples (`exports/sample_transits.csv`), ICS templates from Venus Cycle Analytics, SQLite schema dumps (`schemas/sqlite/transits_events.sql`).
- **Downstream links**: CLI exporters (`astroengine.exports`), QA fixtures (`tests/exports/test_interop_contracts.py`), release ops documentation (`docs/module/release_ops.md`).

This specification defines the serialization formats that guarantee deterministic exchanges between AstroEngine and external systems. All field definitions map to existing schema files or Solar Fire exports; no synthetic fields are introduced.

## AstroJSON Schemas

### `natal_v1`

- **Location**: `schemas/astrojson/natal_v1.json`
- **Purpose**: Represent natal chart metadata for Solar Fire ingest and AstroEngine runtime.
- **Required fields**:
  - `chart_id` (UUID, references `profiles/natal_index.csv`)
  - `name`
  - `datetime_utc`
  - `timezone` (IANA tzid)
  - `location` object: `lat`, `lon`, `altitude_m`, `atlas_urn`
  - `house_system`
  - `profiles` (list of profile IDs)
- **Optional fields**: `notes`, `source_dataset`
- **Provenance**: Each record includes `source_checksum` referencing Solar Fire export row, ensuring traceability.

### `event_v1`

- **Location**: `schemas/astrojson/event_v1.json`
- **Purpose**: Capture runtime event detections (stations, ingresses, etc.).
- **Fields**:
  - `event_id` (UUID)
  - `module_path` (module/submodule/channel/subchannel string)
  - `event_kind`
  - `timestamp_utc`
  - `bodies` array with `id`, `role`, `longitude_deg`, `latitude_deg`, `declination_deg`, `speed_deg_per_day`
  - `severity` object: `score`, `band`, `modifiers`
  - `provenance` object: dataset URNs, Solar Fire row references, ephemeris checksum
  - `exports` array referencing downstream channels engaged by the rule

### `transit_v1`

- **Location**: `schemas/astrojson/transit_v1.json`
- **Purpose**: Provide rolled-up transit forecasts for UI and ICS conversions.
- **Fields**: merges relevant pieces from `event_v1` plus user-specific schedule metadata: `window_start_utc`, `window_end_utc`, `channel_id`, `profile_id`, `notification_targets`.

All AstroJSON schemas require schema versioning with `schema_version` field and `semantic_version` string to track migrations.

## CSV/Parquet Exports

- **Default CSV columns** (Solar Fire parity):
  - `timestamp_utc`, `event_kind`, `body`, `natal_reference`, `aspect`, `orb_deg`, `severity_score`, `severity_band`, `profile_id`, `dataset_urn`.
- **Encoding**: UTF-8, RFC 4180 line endings, quoting minimal.
- **Partitioning**: For Parquet exports, partition by `profile_id` and `event_kind` to allow efficient range scans.
- **Compression**: Use `snappy` for Parquet, `gzip` for CSV optional output.
- **Provenance**: Each file accompanies a JSON sidecar containing `source_checksum`, `exporter_version`, `row_count`.

## SQLite Schema (`transits_events`)

- **File**: `schemas/sqlite/transits_events.sql`
- **Tables**:
  - `events` (`event_id` PRIMARY KEY, `timestamp_utc`, `event_kind`, `module_path`, `severity_score`, `severity_band`, `profile_id`, `provenance_json`)
  - `bodies` (`body_id`, `event_id` FK, `role`, `longitude_deg`, `latitude_deg`, `declination_deg`, `speed_deg_per_day`)
  - `exports` (`export_id`, `event_id` FK, `channel_id`, `status`, `last_attempt_utc`)
  - `datasets` (`dataset_urn`, `checksum`, `last_verified`)
- **Indices**:
  - `idx_events_profile_time` on (`profile_id`, `timestamp_utc`)
  - `idx_exports_channel_status` on (`channel_id`, `status`)
- **Foreign keys**: enforce cascading deletes to prevent orphaned rows when events purge. Deletion occurs only after export retention policy satisfied.

## ICS Event Format

- **SUMMARY**: `[{severity_band}] {event_kind} — {body}`
- **DESCRIPTION**: multiline string containing severity breakdown, dataset URNs, Solar Fire references, and instructions for verifying within Solar Fire.
- **DTSTART/DTEND**: derived from `window_start_utc`/`window_end_utc`. Use UTC (`Z`) suffix.
- **UID**: event UUID with domain `astroengine.io`.
- **PRODID**: `-//AstroEngine//Transit Alerts {version}//EN`
- **PRIORITY**: map severity band to ICS priority (Peak=1, Strong=3, Moderate=5, Weak=7).
- **VALARM**: optional, triggered 30 minutes before event; include dataset URN in description.

## Provenance Requirements

- Every export channel must attach dataset URNs in the payload (`provenance` field) referencing real checksums from `docs/module/data-packs.md`.
- Exporters log `export_id`, `channel_id`, `destination`, `status`, `checksum` to `astroengine.infrastructure.observability`.
- When schemas evolve, increment `schema_version` and supply migration notes in `docs/burndown.md`.

## Compatibility Matrix Stub

- Maintain mapping (documented in `docs/module/release_ops.md`) connecting registry modules to export channels to ensure additions never remove existing modules.
- Example row:

| Module path | AstroJSON schema | CSV channel | SQLite table | ICS template |
| ----------- | ---------------- | ----------- | ------------ | ------------ |
| `event-detectors/stations/direct` | `event_v1` | `transits_events.csv` | `events` | `station_alert.ics` |

This interop specification keeps all export formats synchronized with real data sources and enforces traceability for every emitted event.
