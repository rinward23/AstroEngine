# Canonical export schema

AstroEngine persists canonical transit events in a versioned SQLite table named
`transits_events`. The schema is managed through Alembic migrations and aligns
with the Parquet/ICS exporters.

## SQLite (`transits_events`)

| Column       | Type     | Description                                                     |
| ------------ | -------- | --------------------------------------------------------------- |
| `ts`         | TEXT     | ISO-8601 UTC timestamp of the contact.                          |
| `moving`     | TEXT     | Transiting body identifier (e.g., `Mars`).                      |
| `target`     | TEXT     | Natal point identifier or ingress target.                      |
| `aspect`     | TEXT     | Canonical aspect or event keyword (`return`, `ingress`, ...).   |
| `orb`        | REAL     | Signed orb in degrees (negative = applying).                    |
| `orb_abs`    | REAL     | Absolute orb in degrees.                                        |
| `applying`   | INTEGER  | `1` when the contact is applying, `0` otherwise.                |
| `score`      | REAL     | Optional numeric score produced by detectors/profiles.          |
| `profile_id` | TEXT     | Profile provenance (nullable).                                  |
| `natal_id`   | TEXT     | Natal identifier used for provenance and partitioning.          |
| `event_year` | INTEGER  | Extracted calendar year of `ts` for fast filtering.             |
| `meta_json`  | TEXT     | Lossless JSON blob of event metadata.                           |

Indices:

- `ix_transits_events_profile_ts` on (`profile_id`, `ts`).
- `ix_transits_events_natal_year` on (`natal_id`, `event_year`).
- `ix_transits_events_score` on (`score`).

Use `astroengine.infrastructure.storage.sqlite.ensure_sqlite_schema(path)` or
`SQLiteMigrator(path).upgrade()` to initialise/upgrade the schema before
running manual SQL. `sqlite_read_canonical(path)` returns `TransitEvent`
instances with the original metadata restored.

## Parquet dataset

`write_parquet_canonical` produces a dataset partitioned by
`natal_id/event_year`. Each row mirrors the SQLite schema (including the
`meta_json` payload) so filters can be pushed down efficiently:

```python
import pyarrow.dataset as ds

table = ds.dataset("events_ds").to_table(filter=ds.field("natal_id") == "n001")
```

The exporter accepts a `compression` keyword (`snappy` by default) to control
codec selection.

## ICS exports

`write_ics` consumes transit, ingress, or return events and exposes template
hooks for the summary and description fields:

```python
from astroengine.exporters_ics import write_ics

write_ics("events.ics", events, summary_template="{label} [{natal_id}]")
```

Calendar metadata is embedded through `NAME`/`X-WR-CALNAME` headers and each
event UID is derived from canonical payload identifiers.
