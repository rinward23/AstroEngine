# Sidereal & Ayanāṁśa Configuration

AstroEngine supports sidereal workflows by combining three components:

1. **Feature flags** in ``profiles/base_profile.yaml`` turn on the
   sidereal pipeline and select the default ayanāṁśa.
2. **Chart configuration** via :class:`astroengine.chart.config.ChartConfig`
   enforces the tropical vs. sidereal contract and the selected house
   system.
3. **Schemas** under ``schemas/natal_input_v1_ext.json`` document the
   allowed ayanāṁśa identifiers so integrations can validate user input.

## Enabling sidereal mode in a profile

Locate the ``sidereal`` block inside ``profiles/base_profile.yaml``. The
shipped defaults keep sidereal disabled:

```yaml
sidereal:
  enabled: false
  ayanamsha: lahiri
```

Create a profile overlay (see the [Profiles guide](profiles.md)) that sets ``enabled`` to
``true`` and chooses the desired ayanāṁśa. Keep the value lowercase and
stick to the enumerations published in the schema file.

```yaml
sidereal:
  enabled: true
  ayanamsha: krishnamurti
```

Merge the overlay into your scan context with
``profile_into_ctx``. The ``flags`` section of the resulting context will
now advertise ``sidereal.enabled`` and ``sidereal.ayanamsha`` to every
module that needs to adjust coordinate transforms.

## Discovering supported ayanāṁśas

The helper below prints the list maintained by
``schemas/natal_input_v1_ext.json`` so you can double-check spellings
before wiring a profile overlay:

```python
import json
from pathlib import Path

schema = json.loads(Path("schemas/natal_input_v1_ext.json").read_text(encoding="utf-8"))
ayanamshas = [name for name in schema["properties"]["zodiac"]["enum"] if name.startswith("sidereal_")]
print(sorted(ayanamshas))
```

## Valid ChartConfig combinations

:class:`astroengine.chart.config.ChartConfig` ensures that sidereal charts
always include an ayanāṁśa and that tropical charts never do. Attempting
invalid combinations raises ``ValueError`` with a helpful description:

```python
from astroengine.chart.config import ChartConfig

# This succeeds
ChartConfig(zodiac="sidereal", ayanamsha="lahiri", house_system="whole_sign")

# This fails: tropical charts must not specify an ayanāṁśa
ChartConfig(zodiac="tropical", ayanamsha="lahiri")
```

Use ``ChartConfig`` when constructing natal, progressed, or return
charts. Downstream modules (progressions, time-lords, mundane scans)
read the normalized values stored on the config object and adapt their
coordinate transforms accordingly.

## Provenance expectations

A sidereal deployment must document the source of the ayanāṁśa offsets.
If Solar Fire provides the reference offsets, capture the export hash in
``docs/governance/data_revision_policy.md`` before changing a profile.
When importing published ayanāṁśa tables cite the original author and
publication year alongside the raw data file.
