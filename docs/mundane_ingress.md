# Mundane & Ingress Planning

Mundane work in AstroEngine focuses on national charts, Aries ingress
studies, and locality-sensitive forecasting. The design goals are
captured in ``docs/MUNDANE_SPEC.md``—keep orbs conservative, cite every
source chart, and surface provenance in exported data.

## Feature toggles

The ``ingresses`` block in ``profiles/base_profile.yaml`` controls
whether ingress detections run. Keep the defaults in place until the
project ships the dedicated detector channel:

```yaml
ingresses:
  enabled: true
  include_moon: false
  inner_mode: angles_only
```

Setting ``include_moon`` to ``true`` will instruct the future detector to
emit the Moon’s rapid sign changes. The ``inner_mode`` setting determines
whether Mercury and Venus ingresses are always reported or only when
angles are involved.

## Manual Aries ingress check

Until the automated channel lands you can verify ephemeris health by
locating the Aries ingress manually. The script below samples the Sun’s
longitude over a ten-day window and reports the first timestamp inside
Aries (0°–30°):

```python
from datetime import datetime, timedelta, timezone

from astroengine.chart.natal import DEFAULT_BODIES
from astroengine.core.angles import normalize_degrees
from astroengine.ephemeris.swisseph_adapter import SwissEphemerisAdapter

adapter = SwissEphemerisAdapter()
body_code = DEFAULT_BODIES["Sun"]

start = datetime(2024, 3, 15, tzinfo=timezone.utc)
end = datetime(2024, 3, 25, tzinfo=timezone.utc)
step = timedelta(hours=1)

current = start
previous_sign = None
while current <= end:
    jd = adapter.julian_day(current)
    pos = adapter.body_position(jd, body_code, body_name="Sun")
    lon = normalize_degrees(pos.longitude)
    sign_index = int(lon // 30)
    if previous_sign is not None and sign_index != previous_sign:
        print("Aries ingress at", current.isoformat())
        break
    previous_sign = sign_index
    current += step
else:
    raise RuntimeError("Sun did not change signs inside the window")
```

The output is deterministic because it uses the Swiss ephemeris bindings
(or the documented fallback). Recording the ingress timestamp alongside
the profile ID gives mundane analysts a reproducible checkpoint.

## Data management

Mundane charts and ingress research often depend on large data sets
(national founding charts, meteorological baselines, eclipse paths). Use
SQLite for anything larger than a few hundred rows, store the checksum in
``docs/governance/data_revision_policy.md``, and archive the raw exports
alongside the repository. Never fill gaps with synthetic data—when a
source chart is missing, log the omission instead of inventing values.

## Roadmap hooks

When the ingress detector ships it will plug into:

- The transit scanner via the ``ingresses`` feature flag.
- The exporter layer so every ingress event carries its provenance
  metadata.
- Mundane dashboards that correlate ingress hits with national charts in
  ``datasets/``.

Update this document with the command examples once the detector is
integrated so new users can reproduce the full workflow without external
help.
