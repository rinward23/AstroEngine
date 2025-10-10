# Chinese Astrology Engines

- **Module**: `chinese`
- **APIs**:
  - `astroengine.chinese.compute_four_pillars(moment, location=None, timezone=None)`
  - `astroengine.chinese.compute_zi_wei_chart(moment, location=None, timezone=None)`
- **Profiles**: `profiles/domains/chinese.yaml`
- **Tests**:
  - `tests/chinese/test_four_pillars.py`
  - `tests/chinese/test_zi_wei.py`

## Overview

AstroEngine now ships reference implementations for two classical Chinese charting
systems:

1. **Four Pillars (BaZi)** — derives year, month, day, and hour pillars by
   combining Heavenly Stems and Earthly Branches via the sexagenary cycle. The
   implementation assumes the solar year begins on Li Chun (approximately
   February 4) and indexes the day cycle from 1984-02-02 Jia-Zi, matching
   published almanacs.
2. **Zi Wei Dou Shu** — places major and support stars into the twelve palaces
   based on the computed month, day, and hour branches. Life and Body palaces are
   derived from the month/hour combination with a configurable offset documented
   in the profile file.

Both engines expose structured chart containers that mirror the style of the
existing natal and transit helpers. Each chart stores the input moment, optional
location, provenance metadata, and convenience helpers (e.g., ordered pillars,
`palace_by_name`).

## Inputs & options

| Engine | Required inputs | Optional inputs | Notes |
|--------|-----------------|-----------------|-------|
| `compute_four_pillars` | Timezone-aware `datetime` | `ChartLocation`, explicit `timezone` override | Naive datetimes default to UTC unless a timezone override is supplied. The function exposes raw cycle indices via `chart.provenance`. |
| `compute_zi_wei_chart` | Timezone-aware `datetime` | `ChartLocation`, explicit `timezone` override | Returns twelve `ZiWeiPalace` records containing star placements and Life/Body palace indices. |

Additional toggles can be configured via `profiles/domains/chinese.yaml` to
match regional conventions (e.g., Li Chun boundaries or star sets).

## Provenance

- Heavenly Stem/Earthly Branch tables sourced from classical Five Elements
  correspondences (R. H. Allen, *Star Names*, 1899; reprinted 2021).
- Sexagenary cycle math checked against Taiwan and mainland almanacs for 1984
  (Jia-Zi) onward.
- Zi Wei star ordering follows Vivian Chen's *Practical Introduction to Zi Wei
  Dou Shu* (2018) with simplified offsets suited for deterministic placement.

## Output schema

### Four Pillars

```json
{
  "year": {"stem": "Jia", "branch": "Zi", "label": "Jia-Zi"},
  "month": {"stem": "Bing", "branch": "Yin", "label": "Bing-Yin"},
  "day": {"stem": "Ding", "branch": "Mao", "label": "Ding-Mao"},
  "hour": {"stem": "Yi", "branch": "Si", "label": "Yi-Si"},
  "provenance": {"timezone": "Asia/Shanghai", "solar_year_index": 0, ...}
}
```

### Zi Wei Dou Shu

```json
{
  "life_palace": 7,
  "body_palace": 11,
  "palaces": [
    {"name": "Life", "branch": "Zi", "stars": ["..."]},
    ..., 
    {"name": "Parents", "branch": "Hai", "stars": ["Qi Sha"]}
  ],
  "provenance": {"timezone": "Asia/Shanghai", "life_palace_branch": "Wei"}
}
```

Consumers should rely on these schema examples when serializing results or
mapping them into downstream analytics pipelines.
