# AstroEngine Knowledge Base

The knowledge base module records the vocabulary, chart types, and
cross-tradition frameworks that AstroEngine exposes through its module
registry. The registry entry is created by
`astroengine.modules.reference.register_reference_module`, which adds a
hierarchy of glossary, chart, and framework submodules to the shared
`AstroRegistry`. 【F:astroengine/modules/reference/__init__.py†L1-L73】

Each entry in the registry stores structured provenance metadata. Runtime
consumers receive a summary plus a list of sources split between the exact
repository path that produced the behaviour and the published text that
verifies the astrological, psychological, or esoteric claims. The
provenance payload is built from the catalog defined in
`astroengine/modules/reference/catalog.py`. 【F:astroengine/modules/reference/catalog.py†L1-L204】

## Glossary of foundational terms

| Term | Definition | AstroEngine implementation | Verified source |
| --- | --- | --- | --- |
| Natal chart | Radix chart computed by `compute_natal_chart`, which queries the Swiss Ephemeris adapter and applies the shared orb policy. | `astroengine/chart/natal.py` | Astrodienst AG, *Swiss Ephemeris for Programmers* (2023). [^1] |
| Transit contact | Aspect detected by `TransitScanner` whenever a moving body forms an allowed angle to a natal position. | `astroengine/chart/transits.py` | Brady, *Predictive Astrology: The Eagle and the Lark* (2008). [^2] |
| Progressed positions | Day-for-a-year secondary progressions mirrored from Solar Fire exports. | `astroengine/chart/progressions.py` | March & McEvers, *The Only Way to Learn Astrology Vol. 3* (1980). [^3] |
| Solar return | Annual return chart produced when the Sun reaches its natal longitude. | `astroengine/chart/returns.py` | Carter, *Solar Returns* (1971). [^4] |
| Composite chart | Relationship midpoint chart that averages two natal datasets. | `astroengine/chart/composite.py` | Hand, *Planets in Composite* (1975). [^5] |
| Aspect orb policy | Registry-wide orb allowances derived from the versioned aspects policy. | `astroengine/scoring/orb.py` | Sakoian & Acker, *The Astrologer's Handbook* (1973). [^6] |
| Ayanāṁśa profile | Sidereal offsets normalised through `ChartConfig` and the Swiss Ephemeris adapter. | `astroengine/chart/config.py` | Fagan & Bradley, *Sidereal Astrology* (1950). [^7] |

The glossary channel is stored at `reference/glossary/definitions` in the
registry. Every subchannel exposes the summary text, a list of source
records that include repository paths, and verifiable citations so runtime
tooling can present provenance next to each definition.
【F:astroengine/modules/reference/__init__.py†L23-L49】【F:astroengine/modules/reference/catalog.py†L26-L111】

## Chart type index

The chart submodule catalogues every chart family that the engine can
materialise from Solar Fire compatible data. Runtime lookups map the slug
to the underlying implementation so UI components can link directly into
the relevant modules. 【F:astroengine/modules/reference/__init__.py†L51-L63】

| Chart type | Description | AstroEngine implementation | Verified source |
| --- | --- | --- | --- |
| Natal chart | Base dataset that anchors timing techniques and synastry overlays. | `astroengine/chart/natal.py` | Astrodienst AG, *Swiss Ephemeris for Programmers* (2023). [^1] |
| Secondary progression | Day-for-a-year advancement for predictive work. | `astroengine/chart/progressions.py` | March & McEvers, *The Only Way to Learn Astrology Vol. 3* (1980). [^3] |
| Planetary return | Solar, lunar, or custom returns aligned to natal longitudes. | `astroengine/chart/returns.py` | Carter, *Solar Returns* (1971). [^4] |
| Synastry overlays | Cross-chart scoring used by the relationship timeline and VCA modules. | `astroengine/synastry/__init__.py` | Greene, *Relating* (1977). [^8] |

## Psychological and esoteric frameworks

The frameworks submodule indexes psychological overlays, tarot
correspondences, and Kabbalistic mappings that enrich AstroEngine's
interpretive layers. Each entry links to the source code that stores the
canonical correspondences and the documentation that describes how the
values were recorded. 【F:astroengine/modules/reference/catalog.py†L153-L204】

| Framework | Description | AstroEngine implementation | Verified source |
| --- | --- | --- | --- |
| Venus Cycle Analytics | Resonance model that blends Venus phases with house and dignity scores. | `astroengine/modules/vca/__init__.py`, `profiles/vca_outline.json` | Rudhyar, *The Lunation Cycle* (1986). [^9] |
| Seven Rays | Esoteric psychology correspondences used across overlay modules. | `astroengine/esoteric/seven_rays.py` | Bailey, *Esoteric Psychology, Volume I* (1936). [^10] |
| Golden Dawn tarot correspondences | Major, minor, and court card mappings. | `astroengine/esoteric/tarot.py` | Regardie, *The Golden Dawn* (1989). [^11] |
| Tree of Life paths | Hebrew letter, planetary, and tarot attributions for Golden Dawn pathworking. | `astroengine/esoteric/tree_of_life.py` | Wang, *The Qabalistic Tarot* (2004). [^12] |

## Astrological indicators registry

The indicators submodule exposes the outline of celestial bodies, house
systems, aspect families, zodiac subdivisions, timing techniques, esoteric
frameworks, cultural lineages, collective cycles, and symbolic overlays that
power runtime charting. The full structure and provenance notes are captured in
the [Astrological indicators outline](astrological_indicators.md). Runtime
clients can query the hierarchy through the `reference.indicators.catalog`
channel in the registry. 【F:docs/reference/astrological_indicators.md†L1-L210】【F:astroengine/modules/reference/__init__.py†L1-L120】

| Indicator family | Summary | Registry path |
| --- | --- | --- |
| Celestial bodies | Luminaries, classical planets, modern additions, and calculated points used across chart engines. | `reference.indicators.catalog.celestial_bodies` |
| House systems | Quadrant, whole-sign, equal, and topocentric routines validated through the Swiss Ephemeris adapter. | `reference.indicators.catalog.house_systems` |
| Aspect families & harmonics | Base, minor, and harmonic aspect groups with shared orb governance. | `reference.indicators.catalog.aspect_families` |
| Zodiac subdivisions | Bounds, decans, dwads, dodekatemoria, and nakṣatra overlays. | `reference.indicators.catalog.zodiac_subdivisions` |
| Timing techniques | Transit, progression, direction, profection, and releasing engines. | `reference.indicators.catalog.timing_techniques` |
| Esoteric systems | Seven Rays, Tree of Life, tarot, and chakra correspondences. | `reference.indicators.catalog.esoteric_systems` |
| Cultural systems | Jyotiṣa, Hellenistic, Mesoamerican, and humanistic frameworks. | `reference.indicators.catalog.cultural_systems` |
| Collective cycles | Outer planet pairs, ingress analytics, eclipse seasons, and planetary phase indexes. | `reference.indicators.catalog.collective_cycles` |
| Symbolic overlays | Arabic parts, fixed stars, asteroid catalogues, and mythopoetic narratives. | `reference.indicators.catalog.symbolic_overlays` |

### Registry integration guarantees

The registry helper accepts new entries without replacing existing
modules, preserving the module → submodule → channel → subchannel hierarchy
required by AstroEngine's governance rules. To extend the knowledge base,
add a new `ReferenceEntry` with at least one repository source and one
externally verifiable citation, then re-run `register_reference_module`.
Tests that assert module registration (for example
`tests/test_module_registry.py`) will surface missing entries so new
definitions remain attached to real data. 【F:astroengine/modules/reference/__init__.py†L9-L73】【F:tests/test_module_registry.py†L1-L50】

## Citations

[^1]: Astrodienst AG. (2023). *Swiss Ephemeris for Programmers: Technical documentation*. Retrieved from https://www.astro.com/swisseph/swephprg.htm
[^2]: Brady, B. (2008). *Predictive Astrology: The Eagle and the Lark*. Weiser Books.
[^3]: March, M. D., & McEvers, J. (1980). *The Only Way to Learn Astrology, Volume 3*. ACS Publications.
[^4]: Carter, C. E. O. (1971). *Solar Returns*. Regulus Publishing Company.
[^5]: Hand, R. (1975). *Planets in Composite*. Whitford Press.
[^6]: Sakoian, F., & Acker, L. (1973). *The Astrologer's Handbook*. HarperCollins.
[^7]: Fagan, C., & Bradley, D. (1950). *Sidereal Astrology*. Llewellyn Publications.
[^8]: Greene, L. (1977). *Relating: An Astrological Guide to Living with Others on a Small Planet*. Weiser Books.
[^9]: Rudhyar, D. (1986). *The Lunation Cycle*. Aurora Press.
[^10]: Bailey, A. A. (1936). *Esoteric Psychology, Volume I*. Lucis Publishing Company.
[^11]: Regardie, I. (1989). *The Golden Dawn*. Llewellyn Publications.
[^12]: Wang, R. (2004). *The Qabalistic Tarot*. Samuel Weiser.
