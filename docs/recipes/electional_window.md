# Recipe: Electional Window Sweep

Use the ``fast_scan`` helper to identify when a transiting body comes
within a desired orb of a natal longitude. This example finds the Moon’s
trine to a natal Sun at 15° Gemini (75° ecliptic longitude) during May
2024.

## Script

```python
from datetime import datetime, timezone
from pprint import pprint

from astroengine.engine import ScanConfig, fast_scan

start = datetime(2024, 5, 1, tzinfo=timezone.utc)
end = datetime(2024, 5, 25, tzinfo=timezone.utc)
config = ScanConfig(
    body=1,              # 1 -> Moon (see astroengine.engine._BODY_CODE_TO_NAME)
    natal_lon_deg=75.0,  # Natal Sun at 15° Gemini
    aspect_angle_deg=120.0,  # Trine
    orb_deg=0.5,         # Half-degree orb
    tick_minutes=30,     # Sample every 30 minutes
)

hits = fast_scan(start, end, config)
print(f"Found {len(hits)} samples")
pprint(hits[:4])
```

Running the snippet prints the timestamps closest to the exact trine. In
this case the Moon perfects the aspect on 19 May 2024 at 17:00 UTC. The
``delta`` column expresses how far the moving body is from the exact
angle in degrees.

## Refining the election

- Decrease ``tick_minutes`` to 10 or 5 minutes for a tighter window once
  the rough hits are known.
- Pipe the ``hits`` through ``astroengine.exporters.write_sqlite_canonical``
  or ``write_parquet_canonical`` after annotating them with additional
  context (location, chosen profile ID).
- Combine the sweep with the daily planner output to ensure other key
  transits reinforce the election.

Because ``fast_scan`` derives its positions from Swiss Ephemeris, every
sample can be traced back to the underlying data files listed in the
profile metadata.
