# Esoteric Overlays Module

- **Module**: `esoterica`
- **Scope**: Tarot, Golden Dawn, Qabalah, alchemy, numerology, I Ching, runes
- **Status**: Expanded – multiple lineages indexed with provenance metadata

The esoteric overlays module now covers the Golden Dawn decans plus additional
symbolic systems demanded by the blueprint: Tree of Life sephiroth and paths,
alchemical stages, the Seven Rays, Golden Dawn grades, extended tarot
correspondences, numerology, the Zhouyi hexagrams, and Elder Futhark runes. Every
table is sourced from a published lineage reference so downstream automation can cite
its authority while composing reports or ritual prompts.

## Registry layout

```
esoterica/
  decans/
    chaldean_order/
      golden_dawn_tarot
  chakras/
    planetary_lineage/
      bihar_school
  tree_of_life/
    sephiroth/
      golden_dawn
    paths/
      attributions
  alchemy/
    operations/
      classical_sequence
  seven_rays/
    bailey_lineage/
      ray_profiles
  initiatory_orders/
    golden_dawn/
      grade_ladder
  tarot/
    majors/
      golden_dawn_paths
    courts/
      book_t_quadrants
    spreads/
      documented_spreads
  numerology/
    digits/
      pythagorean
      master_numbers
  oracular_systems/
    i_ching/
      king_wen_sequence
    runes/
      elder_futhark
```

### Decans

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

### Tree of Life

- `tree_of_life/sephiroth/golden_dawn` enumerates the ten sephiroth with pillar
  placement, spheres, planetary associations, and working keywords (sources: *777*,
  Dion Fortune).
- `tree_of_life/paths/attributions` lists paths 11–32 with Hebrew letters, tarot keys,
  and astrological attributions.

### Alchemy

- `alchemy/operations/classical_sequence` documents the seven-stage Magnum Opus
  sequence (Calcination → Coagulation) as described by Lyndy Abraham and Dennis Hauck.

### Seven Rays

- `seven_rays/bailey_lineage/ray_profiles` records virtues, vices, colours, and
  planetary rulers for Alice A. Bailey's Seven Rays.

### Chakras

- `chakras/planetary_lineage/bihar_school` captures the Bihar School of Yoga
  lineage described by Swami Satyananda Saraswati, aligning each chakra with its
  planetary ruler. Mind/Body/Spirit domain weights follow Anodea Judith's
  psychological framing so downstream VCA analytics can project chakra emphasis
  from chart factors.

### Initiatory Orders

- `initiatory_orders/golden_dawn/grade_ladder` maps the Neophyte → Ipsissimus grade
  structure to sephiroth, elemental lessons, and Regardie-sourced notes.

### Tarot extensions

- `tarot/majors/golden_dawn_paths` aligns the major arcana with Hebrew letters and
  path numbers.
- `tarot/courts/book_t_quadrants` provides Golden Dawn elemental qualities and the
  zodiac spans each court card oversees.
- `tarot/spreads/documented_spreads` bundles three spreads (Golden Dawn triad,
  Waite's Celtic Cross, Elemental Balance) with positional meanings.

### Numerology

- `numerology/digits/pythagorean` indexes digits 0–9 with planetary rulers and
  keywords (Cheiro, Campbell).
- `numerology/digits/master_numbers` adds the 11/22/33 master number set.

### Oracular systems

- `oracular_systems/i_ching/king_wen_sequence` delivers the 64 hexagrams with Chinese
  names, pinyin, translations, and thematic keywords (Wilhelm).
- `oracular_systems/runes/elder_futhark` stores the 24 Elder Futhark runes with
  phonetics, elements, and meanings (Flowers, Paxson).

## Sources

- Hermetic Order of the Golden Dawn — *Book T: The Tarot* (c. 1893)
- Arthur Edward Waite — *The Pictorial Key to the Tarot* (1910)
- Hermetic Order of the Golden Dawn — *777* (1909)
- Dion Fortune — *The Mystical Qabalah* (1935)
- Lyndy Abraham — *A Dictionary of Alchemical Imagery* (1998)
- Dennis William Hauck — *The Complete Idiot's Guide to Alchemy* (2008)
- Alice A. Bailey — *Esoteric Psychology I* (1936)
- Israel Regardie — *The Golden Dawn* (1937)
- Cheiro — *Cheiro's Book of Numbers* (1926)
- Florence Campbell — *Your Days Are Numbered* (1931)
- Richard Wilhelm — *The I Ching or Book of Changes* (1923)
- Stephen Flowers — *Futhark: A Handbook of Rune Magic* (1984)
- Diana L. Paxson — *Taking Up the Runes* (2005)
- Swami Satyananda Saraswati — *Kundalini Tantra* (1984)
- Anodea Judith — *Wheels of Life: A User's Guide to the Chakra System* (1987)

## Runtime helpers

```python
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.esoteric import assign_decans, chakra_emphasis_for_chart

chart = compute_natal_chart(
    moment=...,  # timezone-aware datetime
    location=ChartLocation(latitude=40.7128, longitude=-74.0060),
)
for assignment in assign_decans(chart.positions):
    print(assignment.body, assignment.decan.tarot_card, assignment.decan.tarot_title)

# Estimate chakra emphasis directly from VCA house weighting
print(chakra_emphasis_for_chart(chart))
```

`assign_decans` consumes the same `BodyPosition` objects returned by the natal and
transit engines, guaranteeing the tarot overlay is traceable to the chart data. The
helper returns immutable dataclasses with both the raw longitude and the metadata
payload, making it easy to forward the results to exporters or narrative systems
without losing precision.

## Validation

- Registry smoke-test: `astroengine.modules.DEFAULT_REGISTRY.as_dict()` now includes
the expanded esoteric submodules so automation can crawl the hierarchy.
- Unit tests under `tests/esoteric/test_decans.py` cover longitude normalisation and
assignment logic so future changes cannot silently break the mapping.
