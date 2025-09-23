# Time-lords Module

The time-lords channel organises profections and other period lords
under the predictive module hierarchy. Each implementation must cite the
source tables (Solar Fire exports or published techniques) so no period
is generated without a documented pedigree.

## Current implementation status

``astroengine.timelords.profections.annual_profections`` is checked in as
an explicit stub. It returns an empty list until the profection tables
and validation data sets are imported. Callers should guard against the
empty return value and surface a helpful message to users.

```python
from astroengine.timelords.profections import annual_profections

events = annual_profections(
    natal_ts="1990-05-01T12:00:00Z",
    start_ts="2024-01-01T00:00:00Z",
    end_ts="2025-01-01T00:00:00Z",
    lat=40.7128,
    lon=-74.0060,
)
print(events)  # [] until the profection tables land
```

The function signature already encodes the provenance expectations:
inputs are ISO-8601 timestamps and geographic coordinates so callers can
point back to the original chart data.

## Feature flags

Profiles control access to time-lord techniques through the
``timelords`` section. ``profiles/feature_flags.md`` documents each key:

- ``timelords.enabled`` (boolean toggle)
- ``profections.cycle`` (``annual`` today, ``monthly`` reserved)

Until the underlying data sets ship, keep ``timelords.enabled`` set to
``false`` in production profiles. During development you can turn the
flag on to exercise glue code without emitting user-facing output.

## Data requirements

When the profection tables are imported they must include:

- House assignments for each year of life.
- Ruler mapping for every house, including the nocturnal/diurnal variant
  when the technique requires it.
- Source citations for each mapping (e.g., Solar Fire tables or
  Hellenistic references).

Store the raw tables under ``datasets/`` (CSV or SQLite) and record the
checksums plus reproduction commands in
``docs/governance/data_revision_policy.md``.

## Integration points

Once the data ships, the time-lords module will plug into:

- Transit scanners that annotate events with the active profection ruler.
- Narrative overlays that add context about period lords to generated
  interpretations.
- Exporters (SQLite, Parquet, ICS) via the profile context so every
  exported event carries the time-lord metadata used during the run.

Document each integration in the relevant module guide when you wire it
up so downstream consumers understand how the data flows through the
module → submodule → channel → subchannel hierarchy.
