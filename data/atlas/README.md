# Offline Atlas Sample

This directory contains assets for the offline atlas feature used by
`astroengine.geo.atlas`. A portable SQL script (`offline_sample.sql`) seeds a
minimal SQLite database for validation and demos. The schema is intentionally
simple:

```sql
CREATE TABLE places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT,
    search_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    tzid TEXT NOT NULL,
    population INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX idx_places_search ON places(search_name);
```

Entries must populate `search_name` using the same normalization logic as
`astroengine.geo.atlas._normalize` so lookups remain deterministic. The seed row
provides London, United Kingdom, and acts as the validation target for
`tests/test_geo_atlas.py`.

## Regenerating the sample database

To materialize the SQLite database, run:

```bash
sqlite3 offline_sample.sqlite < offline_sample.sql
```

The resulting `offline_sample.sqlite` file can be referenced via the settings
panel or CLI configuration when exercising offline atlas lookups.

## Selecting the dataset in the UI

The Streamlit settings panel now enumerates SQLite files discovered under
`data/atlas` so you can choose the bundled sample without retyping paths. Pick a
package from the **Bundled offline atlases** dropdown or enter a custom path in
the adjacent text field if your dataset lives elsewhere.

## Online fallback controls

Online geocoding is disabled by default to prioritize reproducible, offline
results. Enable the "Allow online fallback geocoding" toggle in the settings UI
only when you have the `geopy` extra installed and are comfortable querying the
network. When the fallback remains disabled, atlas lookups fail fast with a
message directing you to refresh the offline dataset instead of silently
contacting external services.
