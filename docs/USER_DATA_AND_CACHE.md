# >>> AUTO-GEN BEGIN: docs-user-data-cache v1.0
## User Data Vault
- Location: `~/.astroengine/natals/` (override `ASTROENGINE_HOME`).
- One JSON per natal, named `{natal_id}.json`. Example fields: `natal_id, name, utc, lat, lon, tz, place`.
- CLI:
  - Save: `--save-natal --natal-id alice --natal-utc 1990-01-01T12:00:00Z --lat 40.7 --lon -74.0 --name "Alice" --place "NYC"`
  - List: `--list-natals`
  - Load into a run: `--load-natal alice`
  - Delete: `--delete-natal --natal-id alice`

## Positions Cache
- Location: `~/.astroengine/cache/positions.sqlite`.
- Key: `(day_jd, body)`; stores ecliptic longitude (deg). Populated on demand.
- Enable per run: `--use-cache`. Warm for a window: `--cache-warm`.

## Parquet Dataset (partitioned)
- Use `--export-parquet-dataset out/events_ds` to write partitioned by `natal_id/year`.
- Great with DuckDB/Polars/Spark for analytics and incremental additions.
# >>> AUTO-GEN END: docs-user-data-cache v1.0
