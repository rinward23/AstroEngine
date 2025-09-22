# Esoteric Overlays Module

- **Module**: `esoterica`
- **Scope**: Tarot, Golden Dawn, Chaldean decans
- **Status**: Prototype – foundational dataset wired into registry and runtime helpers

The esoteric overlays module introduces 10° decan divisions with Golden Dawn tarot
correspondences so ritual- and initiatory-focused reports can reference concrete
source material. It fills part of the "mystical correspondences" gap called out in the
esoteric blueprint without inventing synthetic data – every value is pulled directly
from the published Golden Dawn sequence.

## Registry layout

```
esoterica/
  decans/
    chaldean_order/
      golden_dawn_tarot
```

The `golden_dawn_tarot` subchannel payload contains 36 objects with the following
fields:

| Field | Description |
| --- | --- |
| `index` | Absolute decan index in the 0–35 range. |
| `sign` | Tropical zodiac sign owning the decan. |
| `sign_index` | Numeric index of the sign (Aries=0 … Pisces=11). |
| `decan_index` | Ordinal within the sign (0–2). |
| `start_degree` / `end_degree` | Absolute ecliptic bounds in degrees. |
| `ruler` | Planetary ruler following the Chaldean order. |
| `tarot_card` | Golden Dawn pip card assigned to the decan. |
| `tarot_title` | Traditional title from Book T / Pictorial Key. |

## Sources

- Hermetic Order of the Golden Dawn — *Book T: The Tarot* (c. 1893)
- Arthur Edward Waite — *The Pictorial Key to the Tarot* (1910)

## Runtime helpers

```python
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.esoteric import assign_decans

chart = compute_natal_chart(
    moment=...,  # timezone-aware datetime
    location=ChartLocation(latitude=40.7128, longitude=-74.0060),
)
for assignment in assign_decans(chart.positions):
    print(assignment.body, assignment.decan.tarot_card, assignment.decan.tarot_title)
```

`assign_decans` consumes the same `BodyPosition` objects returned by the natal and
transit engines, guaranteeing the tarot overlay is traceable to the chart data. The
helper returns immutable dataclasses with both the raw longitude and the metadata
payload, making it easy to forward the results to exporters or narrative systems
without losing precision.

## Validation

- Registry smoke-test: `astroengine.modules.DEFAULT_REGISTRY.as_dict()` now includes
the `esoterica/decans/chaldean_order/golden_dawn_tarot` path, ensuring automation
can crawl the hierarchy.
- Unit tests under `tests/esoteric/test_decans.py` cover longitude normalisation and
assignment logic so future changes cannot silently break the mapping.
