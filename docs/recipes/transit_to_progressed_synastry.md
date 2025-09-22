# Recipe: Transit-to-Progressed Synastry

This workflow compares transiting planets against secondary progressed
positions for the same native. The example focuses on Sun/Moon/Venus/Mars
contacts during the first quarter of 2024.

## Script

```python
from datetime import datetime, timezone
from pprint import pprint

from astroengine.chart.natal import DEFAULT_BODIES
from astroengine.core.angles import delta_angle, normalize_degrees
from astroengine.detectors.progressions import secondary_progressions
from astroengine.ephemeris.swisseph_adapter import SwissEphemerisAdapter

BODIES = ["Sun", "Moon", "Venus", "Mars"]
ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}
ORB_DEG = 1.0

progressions = secondary_progressions(
    natal_iso="1990-05-01T12:30:00Z",
    start_iso="2024-01-01T00:00:00Z",
    end_iso="2024-03-31T00:00:00Z",
    bodies=BODIES,
    step_days=7.0,  # weekly samples keep the table manageable
)

adapter = SwissEphemerisAdapter()
body_map = {name: DEFAULT_BODIES[name] for name in BODIES}
synastry_hits = []

for event in progressions:
    sample_dt = datetime.fromisoformat(event.ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    jd = adapter.julian_day(sample_dt)
    transit_positions = adapter.body_positions(jd, body_map)

    for transit_name, transit_position in transit_positions.items():
        transit_lon = normalize_degrees(transit_position.longitude)
        for progressed_name in BODIES:
            progressed_lon = event.positions[progressed_name]
            for angle_deg, label in ASPECTS.items():
                target = (progressed_lon + angle_deg) % 360.0
                separation = abs(delta_angle(transit_lon, target))
                if separation <= ORB_DEG:
                    synastry_hits.append(
                        {
                            "ts": event.ts,
                            "transit": transit_name,
                            "progressed": progressed_name,
                            "aspect": label,
                            "orb_deg": round(separation, 3),
                        }
                    )

synastry_hits.sort(key=lambda row: (row["ts"], row["transit"], row["progressed"]))
pprint(synastry_hits)
```

The output lists every transit-progressed contact that falls within the
one-degree orb. Because both the transits and the progressions rely on
Swiss Ephemeris calculations, the resulting synastry table can be traced
back to published ephemeris files.

## Variations

- Decrease ``step_days`` to 1.0 when you need daily progressions.
- Restrict ``BODIES`` to the pairs you care about (e.g., Venus ↔ Mars).
- Add severity weighting by mapping the hits into canonical
  ``TransitEvent`` objects and feeding them through the scoring helpers
  referenced in ``profiles/base_profile.yaml``.
