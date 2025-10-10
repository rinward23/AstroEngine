# Astrological indicators outline

The astrological indicators registry organises the observable, computed, and
documentary signals that AstroEngine tracks across its modules. Each indicator
summarises the subcomponents that contribute to a reading and lists the
repository artefacts and publications that substantiate the workflow. Runtime
consumers can traverse these categories through the `reference.indicators`
channel registered in the shared `AstroRegistry`.

## Celestial bodies

### Outline

- **Luminaries** — Sun and Moon definitions, including visibility metadata and
  phase tagging rules shared with the prediction engines.
- **Classical planets** — Mercury through Saturn codes that anchor natal,
  synodic, and mundane analytics.
- **Modern additions** — Uranus, Neptune, Pluto, and selectable asteroids used
  by elective and research pipelines.
- **Calculated points** — Lunar nodes, Lilith, Vertex, Part of Fortune, and
  related points derived from Swiss Ephemeris routines.

### Provenance notes

- `astroengine/chart/natal.py` documents the `DEFAULT_BODIES` mapping used by
  every chart factory.【F:astroengine/chart/natal.py†L25-L117】
- `profiles/base_profile.yaml` records registry defaults for enabled bodies and
  asteroid packs.【F:profiles/base_profile.yaml†L1-L320】
- Astrodienst AG, *Swiss Ephemeris for Programmers* (2023) describes the
  algorithms that resolve planetary and point positions.【F:docs/reference/knowledge_base.md†L1-L160】

## House systems

### Outline

- **Quadrant systems** — Placidus, Koch, Regiomontanus, and Campanus options
  used by horary and psychological modules.
- **Whole-sign and equal** — Classical whole-sign, equal sign, and equal MC
  configurations for Hellenistic, Jyotiṣa, and electional tooling.
- **Topocentric derivatives** — Horizontal, Morinus, and Alcabitius selections
  surfaced through the Swiss Ephemeris adapter for research scenarios.
- **Dynamic validation** — Provenance logging that records requested versus
  computed systems for every chart invocation.

### Provenance notes

- `core/houses_plus/engine.py` lists the supported house keys exposed through
  the compute API.【F:core/houses_plus/engine.py†L64-L109】
- `astroengine/chart/config.py` normalises configuration requests and rejects
  unsupported systems.【F:astroengine/chart/config.py†L47-L117】
- Swiss Ephemeris documentation confirms the availability of quadrant and
  horizontal house routines leveraged by the adapter.【F:docs/reference/knowledge_base.md†L1-L160】

## Aspect families and harmonics

### Outline

- **Ptolemaic base** — Conjunction, opposition, square, trine, and sextile as
  the default scoring kernel.
- **Minor aspects** — Semi-sextile, semi-square, sesquiquadrate, quincunx, and
  quintile derivations.
- **Harmonic expansions** — Septile, novile, decile, duodecile, and other
  fractional families enumerated in the scoring policies.
- **Orb governance** — Policy-driven orb tolerances that merge base and harmonic
  families into deterministic aspect searches.

### Provenance notes

- `astroengine/core/aspects_plus/harmonics.py` enumerates canonical angles and
  harmonic derivations.【F:astroengine/core/aspects_plus/harmonics.py†L1-L122】
- `profiles/aspects_policy.json` stores enabled families, harmonics, and orb
  overrides for runtime scoring.【F:profiles/aspects_policy.json†L1-L120】
- Noel Tyl, *The Quindecile* (2001) and Solar Fire harmonic extensions provide
  the interpretive justification for extended angles.【F:docs/module/core-transit-math.md†L38-L70】

## Zodiac subdivisions

### Outline

- **Bounds/terms** — Egyptian and Ptolemaic bounds keyed by sign degree ranges.
- **Decans/faces** — Chaldean and Golden Dawn decans mapped to tarot
  correspondences.
- **Dwads and dodekatemoria** — Optional twelfth-parts for Jyotiṣa and
  Hellenistic techniques.
- **Nakṣatra overlays** — Sidereal lunar mansions cross-referenced with
  planetary rulers and pada subdivisions.

### Provenance notes

- `profiles/dignities.csv` contains bounds, decans, and scoring modifiers used
  by traditional engines.【F:profiles/dignities.csv†L1-L200】
- `astroengine/esoteric/decans.py` links decans to tarot correspondences and
  registry payloads.【F:astroengine/esoteric/decans.py†L1-L210】
- Dennis Harness, *The Nakshatras: The Lunar Mansions of Vedic Astrology* (1999)
  underpins the Jyotiṣa nakṣatra dataset.【F:astroengine/jyotish/data.py†L1-L200】

## Timing techniques

### Outline

- **Transits** — Sliding window detections across natal and mundane datasets.
- **Secondary progressions** — Day-for-a-year movements with parity fixtures
  against Solar Fire exports.
- **Primary directions** — Solar arc and converse directions supporting forecast
  analytics.
- **Profections and distributions** — Annual and monthly profections, zodiacal
  releasing, and other time-lord frameworks.

### Provenance notes

- `astroengine/chart/transits.py`, `progressions.py`, and `directions.py`
  implement the core predictive engines.【F:astroengine/chart/transits.py†L1-L200】【F:astroengine/chart/progressions.py†L1-L160】【F:astroengine/chart/directions.py†L1-L200】
- `astroengine/engine/traditional/profections.py` codifies annual profection
  logic.【F:astroengine/engine/traditional/profections.py†L1-L220】
- Bernadette Brady, *Predictive Astrology: The Eagle and the Lark* (2008)
  verifies transit and progression interpretations.【F:docs/reference/knowledge_base.md†L1-L160】

## Esoteric systems

### Outline

- **Seven Rays psychology** — Ray attributes and planetary correspondences used
  in interpretive overlays.
- **Tree of Life paths** — Hebrew letter, tarot, and planetary mappings aligned
  to Golden Dawn tradition.
- **Tarot decan wheel** — Crosswalk between tarot minors, decans, and planetary
  dignities.
- **Chakra and subtle body** — Optional energy centres mapped to planetary and
  elemental themes.

### Provenance notes

- `astroengine/modules/esoteric/__init__.py` registers decans and tarot
  correspondences for the module registry.【F:astroengine/modules/esoteric/__init__.py†L1-L120】
- `astroengine/esoteric/seven_rays.py` preserves ray definitions and planetary
  assignments.【F:astroengine/esoteric/seven_rays.py†L1-L200】
- Alice A. Bailey, *Esoteric Psychology I* (1936) and Israel Regardie, *The
  Golden Dawn* (1989) provide the published reference set.【F:docs/reference/knowledge_base.md†L1-L160】

## Cultural systems

### Outline

- **Jyotiṣa frameworks** — Graha dignities, varga divisions, yogas, and dasa
  scheduling rules.
- **Hellenistic doctrines** — Sect, triplicity rulers, and time-lord schemes
  mirrored from traditional sources.
- **Mesoamerican correlations** — Research-grade Tzolkʼin and Haab mappings for
  comparative cycles.
- **Modern psychological schools** — Humanistic and archetypal mappings aligned
  with Venus Cycle Analytics and synastry modules.

### Provenance notes

- `astroengine/jyotish/__init__.py` exports dasa calculators, yogas, and varga
  scoring routines.【F:astroengine/jyotish/__init__.py†L1-L200】
- `astroengine/engine/traditional/models.py` encodes sect and triplicity logic
  for Hellenistic delineations.【F:astroengine/engine/traditional/models.py†L1-L260】
- Rudhyar, *The Lunation Cycle* (1986) anchors the humanistic cycle correlations
  used by Venus Cycle Analytics.【F:docs/reference/knowledge_base.md†L1-L160】

## Collective cycles

### Outline

- **Outer planet synodic pairs** — Jupiter–Saturn, Saturn–Uranus, and Pluto
  cycles tracked for societal trend analysis.
- **Ingress analytics** — Cardinal ingress charts and mundane scoring grids.
- **Eclipse seasons** — Saros families and nodal cycles recorded for predictive
  dashboards.
- **Planetary phase indexes** — Venus, Mercury, and Mars phase catalogues for
  socio-economic modelling.

### Provenance notes

- `docs/module/mundane/submodules/outer_cycle_analytics.md` documents the cycle
  pairs, harmonic families, and scoring metrics.【F:docs/module/mundane/submodules/outer_cycle_analytics.md†L1-L120】
- `astroengine/mundane/ingress.py` and `ingress_charts.py` generate ingress and
  mundane baselines.【F:astroengine/mundane/ingress.py†L1-L200】【F:astroengine/mundane/ingress_charts.py†L1-L160】
- Venus Cycle Analytics research provides phase metadata for collective trend
  overlays.【F:profiles/vca_outline.json†L1-L140】

## Symbolic overlays

### Outline

- **Arabic parts and lots** — Configurable point formulas referencing chart
  context and event metadata.
- **Fixed star alignments** — Catalogues for paran, heliacal rising, and
  midpoint overlays.
- **Asteroids and hypothetical points** — Extended body sets sourced from
  maintained asteroid packs.
- **Mythopoetic narratives** — Story-driven overlays that tie archetypal motifs
  to chart structures and rituals.

### Provenance notes

- `astroengine/analysis/arabic_parts.py` and `astroengine/engine/lots` provide
  arithmetic and event-based part calculators.【F:astroengine/analysis/arabic_parts.py†L1-L400】【F:astroengine/engine/lots/events.py†L1-L200】
- `astroengine/core/stars_plus` hosts fixed-star lookup tables and scoring
  helpers.【F:astroengine/core/stars_plus/__init__.py†L1-L120】
- `profiles/fixed_stars.csv` lists paran-ready stellar positions and metadata
  for symbolic overlays.【F:profiles/fixed_stars.csv†L1-L200】

## Citations

- Astrodienst AG. (2023). *Swiss Ephemeris for Programmers: Technical documentation*. https://www.astro.com/swisseph/swephprg.htm
- Bailey, A. A. (1936). *Esoteric Psychology I*. Lucis Publishing Company.
- Brady, B. (2008). *Predictive Astrology: The Eagle and the Lark*. Weiser Books.
- Harness, D. F. (1999). *The Nakshatras: The Lunar Mansions of Vedic Astrology*. Lotus Press.
- Regardie, I. (1989). *The Golden Dawn*. Llewellyn Publications.
- Rudhyar, D. (1986). *The Lunation Cycle*. Aurora Press.
- Tyl, N. (2001). *The Quindecile: The Unique Power of High-Sensitivity*. Llewellyn Publications.
