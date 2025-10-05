# Locational maps and outer-cycle timelines

AstroEngine can now emit data products for astrocartography maps, local
space azimuths, and outer-planet cycle timelines. All values are derived
from the Swiss Ephemeris adapters bundled with the engine—no synthetic
coordinates are produced.

## Astrocartography lines

Generate meridian and horizon linework directly from the CLI:

```bash
astroengine locational astrocartography \
  --moment 2020-12-21T13:00:00Z \
  --bodies sun,jupiter,saturn \
  --lat-step 3 \
  --json
```

The command returns a list of ``MapLine`` dictionaries containing the body
name, line type (``MC``, ``IC``, ``ASC``, ``DSC``) and sampled latitude/
longitude points. Feed the JSON into GIS tooling to draw world maps or
overlay angular lines on a projection of your choice.

Python callers can use :func:`astroengine.ux.maps.astrocartography_lines`
for the same payload while keeping everything in-memory. The REST API also
offers ``GET /v1/astrocartography`` which returns a GeoJSON FeatureCollection
ready for mapping front-ends.

## Local space azimuths

Local space vectors translate a timestamp and location into azimuth/altitude
pairs for one or more bodies:

```bash
astroengine locational local-space \
  --moment 2020-12-21T13:00:00Z \
  --lat 40.7128 --lon -74.0060 \
  --bodies sun,moon,mars \
  --json
```

Each vector includes azimuth and altitude in degrees plus the underlying
right ascension/declination metadata. The Python helper
:func:`astroengine.ux.maps.local_space_vectors` returns ``LocalSpaceVector``
instances with the same fields.

## Outer-cycle timeline windows

Use the ``timeline`` CLI to pre-compute windows for outer-planet aspects:

```bash
astroengine timeline outer-cycles \
  --start 2020-01-01T00:00:00Z \
  --end 2021-01-01T00:00:00Z \
  --bodies jupiter,saturn,uranus,neptune,pluto \
  --aspects 0:conjunction,90:square,180:opposition \
  --json
```

The output contains the centre timestamp, corridor width, and metadata for
each detected hit (aspect label, participating bodies, speed differential).
Downstream dashboards can render the ``start``/``end`` values as bands on
calendar or Gantt-style views.

## Operational helpers

Use ``astroengine ops migrate`` to apply Alembic migrations before running
queries:

```bash
astroengine ops migrate --sqlite events.db
```

Follow up with ``astroengine query --narrative`` (see the narrative recipe)
to inspect the top events once the schema is up to date.
