# Recipe: Daily Planner

This workflow produces a planner-style table that lists transits between
selected moving bodies and a natal chart over a 24-hour window. The data
comes directly from Swiss Ephemeris so every timestamp can be audited.

## Prerequisites

- Follow the [Quickstart](../quickstart.md) to install AstroEngine and verify that
  the ``swiss`` provider loads.
- Collect the natal birth time and location (UTC). In this example we use
  1 May 1990, 12:30 UTC at New York City (40.7128° N, 74.0060° W).

## Script

```python
from datetime import datetime, timedelta, timezone
from pprint import pprint

from astroengine.chart.natal import ChartLocation, DEFAULT_BODIES, compute_natal_chart
from astroengine.core.angles import delta_angle, normalize_degrees
from astroengine.ephemeris.swisseph_adapter import SwissEphemerisAdapter

BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}
ORB_DEG = 1.0

# 1. Compute natal positions
natal_chart = compute_natal_chart(
    moment=datetime(1990, 5, 1, 12, 30, tzinfo=timezone.utc),
    location=ChartLocation(latitude=40.7128, longitude=-74.0060),
)
natal_longitudes = {
    name: normalize_degrees(pos.longitude)
    for name, pos in natal_chart.positions.items()
    if name in BODIES
}

# 2. Sample transits hourly across the desired day
adapter = SwissEphemerisAdapter()
start = datetime(2024, 1, 1, tzinfo=timezone.utc)
end = start + timedelta(days=1)
step = timedelta(hours=1)

body_map = {name: DEFAULT_BODIES[name] for name in BODIES}
current = start
planner_rows = []
while current <= end:
    jd = adapter.julian_day(current)
    positions = adapter.body_positions(jd, body_map)
    for body_name, position in positions.items():
        lon = normalize_degrees(position.longitude)
        for natal_name, natal_lon in natal_longitudes.items():
            for angle_deg, label in ASPECTS.items():
                target = (natal_lon + angle_deg) % 360.0
                separation = abs(delta_angle(lon, target))
                if separation <= ORB_DEG:
                    planner_rows.append(
                        {
                            "timestamp": current.isoformat().replace("+00:00", "Z"),
                            "moving": body_name,
                            "target": f"natal_{natal_name}",
                            "aspect": label,
                            "orb_deg": round(separation, 3),
                        }
                    )
    current += step

# 3. Present the planner
planner_rows.sort(key=lambda row: (row["timestamp"], row["moving"], row["target"]))
pprint(planner_rows)
```

Run the script with ``python - <<'PY'``. The output is a list of
``dict`` objects that can be written to JSON, pushed into SQLite, or fed
into ``pandas.DataFrame`` for a richer planner view. Every entry records
an applying or separating hit within one degree of the configured aspect
angles.

## Extending the planner

- Add more bodies to the ``BODIES`` list (e.g., Jupiter, Saturn) or tweak
  the ``ASPECTS`` map to focus on exact angles of interest.
- Reduce ``ORB_DEG`` to tighten the inclusion criteria.
- Store the planner in SQLite via ``astroengine.exporters.write_sqlite_canonical``
  after converting the rows to canonical ``TransitEvent`` objects with
  ``astroengine.canonical.events_from_any``.
