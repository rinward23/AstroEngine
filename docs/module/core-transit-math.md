# Core Transit Math Specification

- **Module**: `core-transit-math`
- **Author**: AstroEngine Ruleset Working Group
- **Date**: 2024-05-27
- **Source datasets**: Swiss Ephemeris DE441 ephemerides, Solar Fire export pack `transits_2023.sf`, AstroEngine ruleset CSV indices (`rulesets/venus_cycle/policy.csv`), fixed star catalogue `resources/fk6_bright_stars.csv`.
- **Version control**: datasets validated against upstream SHA256 manifests recorded in `rulesets/index.yaml`.
- **Downstream links**: severity policy JSON (`schemas/orbs_policy.json`), Venus Cycle Analytics runtime registry (`astroengine/modules/vca`).

This document enumerates the calculations, parameters, and provenance needed to maintain deterministic transit scoring. All numeric defaults correspond to values published in Solar Fire 9 and cross-verified against Swiss Ephemeris where applicable. No synthetic coefficients are introduced: each value maps to a cited dataset or literature source so run sequences always reflect authentic astrometric data.

## A1. Aspect Canon

| Aspect family | Exact angle (°) | Harmonic | Alternate names | Symmetry notes | Primary sources |
| ------------- | --------------- | -------- | ---------------- | -------------- | --------------- |
| Conjunction | 0 | 1 | Conjunction | Symmetric around 0° and 360° | Solar Fire `aspectdefs.qpd`, Swiss Ephemeris aspect matrix |
| Opposition | 180 | 2 | Opposition | Anti-parallel symmetry (θ, 180°−θ) | Same as above |
| Trine | 120 | 3 | Trigon | Threefold symmetry, offsets at 120° increments | Solar Fire definitions |
| Square | 90 | 4 | Quadrature | Fourfold symmetry | Solar Fire definitions |
| Sextile | 60 | 6 | Hexagon | Sixfold symmetry | Solar Fire definitions |
| Quincunx | 150 | 12 | Inconjunct | Reflects 30° complement | Solar Fire optional aspects pack |
| Semi-square | 45 | 8 | Octile | 45° increments | Ebertin, *Combination of Stellar Influences* |
| Sesquiquadrate | 135 | 8 | Trioctile | Complement of semi-square | Ebertin |
| Semi-sextile | 30 | 12 | Duodecile | 30° increments | Kepler College aspect catalog |
| Novile | 40 | 9 | Nonagon | Ninth harmonic | Rudhyar, *Astrology of Personality* |
| Septile | ~51.4286 | 7 | Heptile | Derived from 360°/7; rounding from Solar Fire | Solar Fire harmonic list |
| Biquintile | 144 | 5 | Double quintile | Derived from fifth harmonic | Solar Fire |
| Quintile | 72 | 5 | Quintile | 360°/5 increments | Solar Fire |
| Bi-septile | ~102.8572 | 7 | | Mirror of septile | Solar Fire |
| Tri-septile | ~154.2858 | 7 | | Completes 7th harmonic | Solar Fire |
| Parallel | Declination match | — | Parallel of declination | Symmetric about celestial equator | Solar Fire declination aspects |
| Contra-parallel | Declination sign inversion | — | | Anti-symmetric around equator | Solar Fire |

**Exclusions**: The 11th harmonic series and synthetic midpoint-only harmonics are intentionally excluded until source data with verifiable observational backing is ingested. Deprecated items (biquintile-inverse, semi-octile) remain absent to preserve parity with Solar Fire defaults.

### Visualization guidance

- Circular diagrams should plot longitude on a polar axis, referencing `schemas/result_schema_v1.json` for sign glyph labels.
- Angular separations must wrap continuously modulo 360°, using the `astroengine.core.geometry.angular_distance` helper for reproducible results.
- Declination aspects render on a mirrored vertical axis with degrees of declination; parallel/contra-parallel thresholds draw directly from the orb matrix below.

## A2. Orbs Policy Matrix

Default orb values come from Solar Fire “Default” profile exports and the internal Venus Cycle Analytics CSV. Overrides appear when profiles (e.g., `tight`, `wide`) require a narrower or wider gate. Values are degrees of arc unless otherwise noted.

| Body class | Natal target | Aspect | Default orb | Tight profile (`vca_tight`) | Wide profile (`vca_support`) | Data provenance |
| ---------- | ------------ | ------ | ----------- | --------------------------- | ---------------------------- | --------------- |
| Luminary (Sun/Moon) | Planet | Conjunction | 10° | 8° | 12° | Solar Fire profile `DEFAULT.ASF` |
| Luminary | Angle (ASC/MC) | Conjunction | 8° | 6° | 10° | Solar Fire | 
| Personal planet (Mercury/Venus/Mars) | Planet | Trine/Sextile | 6° | 5° | 7° | Solar Fire |
| Personal planet | Angle | Square | 5° | 4° | 6° | Solar Fire |
| Social planet (Jupiter/Saturn) | Planet | Conjunction | 5° | 4° | 6° | Solar Fire |
| Outer planet (Uranus/Neptune/Pluto) | Planet | Opposition | 4° | 3° | 5° | Solar Fire |
| Minor planet (Ceres, Pallas, Juno, Vesta) | Planet | Sextile | 3° | 2° | 4° | AstroEngine `data_packs/minor_planets.csv` |
| Fixed star (bright list) | Planet | Parallel | 1° declination | 0°40′ | 1°20′ | `resources/fk6_bright_stars.csv` |
| Lunar Node | Planet | Square | 4° | 3° | 5° | Solar Fire |
| Partile trigger (exact) | Any | Any | 0°10′ | 0°05′ | 0°15′ | AstroEngine severity appendix |

**Interpolation rules**:

1. When multiple profiles apply, choose the narrowest orb to preserve deterministic scoring. Conflicts are logged via `astroengine.infrastructure.observability` with severity `WARNING` and the registry node identifier.
2. Declination aspects apply orb limits symmetrically around the target declination; convert arcminutes to decimal degrees for storage.
3. Midpoint contexts subtract 1° from the selected profile orb and clamp to a minimum of 0°20′.

### Overrides and fallbacks

- Retrograde stations add +0°30′ to conjunction and opposition orbs for the involved body class, acknowledging Solar Fire’s empirical settings.
- Combust windows (Sun conjunction Mercury/Venus) enforce a dynamic orb using the Solar Fire combustion table; severity weighting increases quadratically as Δλ approaches zero.
- If dataset provenance cannot be validated (checksum mismatch), the runtime refuses to evaluate the orb and raises `OrbsPolicyIntegrityError` to prevent synthetic substitution.

## A3. Severity Model

Severity scoring multiplies harmonic weightings, orb falloff, dignity modifiers, and temporal flags. The canonical formula:

```
score = base_weight(body, aspect) * orb_curve(Δλ) * dignity_modifier * phase_modifier * context_multiplier
```

- **Base weights**: derived from Solar Fire `VCA_WEIGHTS.CSV`. Luminary conjunction = 1.0, trine = 0.75, square/opposition = 0.9, sextile = 0.6, quincunx = 0.5, minor aspect baseline = 0.35.
- **Orb curve**: quadratic falloff `orb_curve(Δλ) = max(0, 1 - (Δλ / orb_limit)^2)`; Δλ uses shortest angular distance. For declination, substitute Δδ.
- **Dignity modifier**: computed from `rulesets/venus_cycle/dignities.csv`, mapping essential dignity tiers: domicile +0.15, exaltation +0.1, detriment −0.15, fall −0.1. When conflicting dignities occur (e.g., day vs. night triplicity), apply the natal chart’s sect flag.
- **Phase modifier**: applying aspect +0.05, separating −0.05; retrograde adds +0.07; station exactness multiplies by 1.1.
- **Context multiplier**: angles ×1.15, fixed star alignment ×1.05, midpoint triggers ×0.9.

Band thresholds:

| Band | Score range | Interpretation |
| ---- | ----------- | -------------- |
| Weak | 0.00–0.24 | Below reporting threshold; aggregated for analytics only |
| Moderate | 0.25–0.49 | Report in summary streams |
| Strong | 0.50–0.79 | Trigger notification channels |
| Peak | ≥0.80 | High-priority alerts with detailed provenance |

All thresholds are validated against Solar Fire time-series exports dated 2023-01-01 through 2023-12-31 for Venus Cycle cases. Severity scores must log contributing factors (body weight, orb ratio, modifiers) to ensure traceability.

## A4. Applying vs. Separating & Δλ Continuity

**Definitions**:

- `Δλ = λ_transiting - λ_natal`, normalized to (−180°, +180°].
- An aspect is **applying** when the derivative of Δλ with respect to time tends toward zero with the absolute value decreasing, and **separating** otherwise. Retrograde motion uses instantaneous longitudinal velocity from Swiss Ephemeris `ephemeris_state` calls.
- At 0°/360° crossings, wrap Δλ using `astroengine.core.geometry.wrap_delta_longitude` so continuity is preserved and no discontinuity occurs at Aries 0°.

**Retrograde loops**:

- When speed crosses zero within ±0°20′ of the exact aspect, classify as `stationary_applying` or `stationary_separating` based on forward/backward motion before the station.
- Multi-body midpoint triggers compute Δλ relative to the midpoint longitude `(λ1 + λ2)/2`, normalized with the same wrapping rules. If the midpoint spans 360°, use the modular average defined in `astroengine.core.midpoints.modular_average`.

**Edge cases**:

- High latitude charts requiring topocentric adjustments must use the observer latitude/longitude stored in the natal dataset; fallback to geocentric if missing data is detected to avoid inferred values.
- Declination aspects rely on continuous Δδ; when crossing the celestial equator, maintain sign continuity to avoid artificial discontinuities.

**Observability hooks**:

- Emit structured logs containing `aspect_family`, `delta_longitude`, `delta_declination`, `applying_flag`, `station_flag`, `profile_id`, and dataset checksums.
- Attach provenance URNs referencing Solar Fire export rows (e.g., `sf9://transits_2023.sf#row=5821`) for every evaluation to prove data lineage.

---

By codifying the canonical aspect list, orb policies, severity calculations, and continuity rules with explicit dataset references, this module ensures upgrades can extend the registry without ever removing modules or relying on fabricated coefficients.
