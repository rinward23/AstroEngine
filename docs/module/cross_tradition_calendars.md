# Cross-cultural calendar systems

AstroEngine now bundles converters and symbolism tables for Chinese,
Mayan, and Tibetan traditions under `astroengine.systems`.  These
helpers mirror the structure of the Jyotish data modules: each package
exposes calendar conversion routines, zodiac/house computations, and
symbolic correspondences with clear provenance.

## Accessing the systems package

```python
from astroengine import systems
from datetime import datetime

moment = datetime(1949, 10, 1, 15, 0)

lunar = systems.chinese.chinese_lunar_from_gregorian(moment)
pillars = systems.chinese.four_pillars_from_moment(moment)
long_count = systems.mayan.long_count_from_gregorian(moment)
rabjung = systems.tibetan.gregorian_year_to_rabjung(moment.year)
```

The Chinese helper returns Hong Kong Observatory–sourced lunar dates
between 1900 and 2099 and BaZi four pillars aligned with Helmer
Aslaksen's formulas.  The Mayan module implements the GMT correlation
(584283) for Long Count and calendar-round calculations.  The Tibetan
module resolves rabjung cycles, parkha trigrams, and nine mewa numbers
following Philippe Cornu's cycle rules.

## Natal chart integration

`astroengine.chart.natal.compute_natal_chart` accepts a `traditions`
argument so downstream code can request precomputed cultural metadata.
`traditions` can be a string or sequence of strings:

```python
from astroengine.chart import ChartLocation, compute_natal_chart

chart = compute_natal_chart(
    moment=moment,
    location=ChartLocation(latitude=39.9042, longitude=116.4074),
    traditions=("chinese", "mayan", "tibetan"),
)

print(chart.metadata["traditions"]["mayan"]["long_count"])
```

The returned metadata block contains:

- **Chinese**: Gregorian↔︎lunar conversion plus year/month/day/hour
  pillar pairs and the zodiac animal for the event moment.
- **Mayan**: Long Count components, total elapsed days, calendar round
  labels, and the GMT correlation constant used in conversions.
- **Tibetan**: Rabjung cycle number, year-in-cycle, element/animal,
  gender, parkha trigram, nine mewa number, and the cycle's Gregorian
  start year.

This interface keeps tradition-specific context alongside the Swiss
Ephemeris output, making it straightforward to render culturally aware
charts or pass structured data to downstream scoring modules.

## Registry wiring

All three systems register their reference tables with the
`AstroRegistry` via the new `astroengine.modules.chinese`, `.mayan`, and
`.tibetan` modules.  Bootstrapping the default registry automatically
includes:

- Hong Kong Observatory lunar metadata (1900–2099).
- Tzolk'in day names, Haab month names, Lords of the Night, and the GMT
  correlation constant.
- Tibetan five-element and parkha symbolism aligned with rabjung cycles.

This mirrors the existing Jyotish wiring so external consumers can query
metadata without hard-coding file paths or duplicate tables.

