# Core Transit Math Specification

- **Module**: `core-transit-math`
- **Maintainer**: Runtime & Scoring Guild
- **Source artifacts**:
  - `astroengine/modules/vca/rulesets.py` for the baked-in aspect catalogue and orb-class defaults.
  - `profiles/base_profile.yaml` for transit orbs, severity weights, combustion windows, and feature toggles used by detectors.
  - `profiles/vca_outline.json` for domain weighting presets that feed the scoring helpers in `astroengine/core/scoring.py`.
  - `profiles/dignities.csv` and `profiles/fixed_stars.csv` for the dignity and fixed-star modifiers referenced by severity rules.
  - `schemas/orbs_policy.json` for profile-specific orb multipliers exposed to downstream tooling.

AstroEngine exposes the transit mathematics through a registry-backed module → submodule → channel → subchannel structure. This document records the authoritative constants shipped in the repository so that run sequences remain reproducible and backed by real files. All values referenced below are validated in the automated suite (`tests/test_vca_ruleset.py`, `tests/test_orbs_policy.py`, `tests/test_domain_scoring.py`, `tests/test_domains.py`, and `tests/test_vca_profile.py`).

## Aspect canon

`VCA_RULESET` enumerates every aspect supported by the default Venus Cycle Analytics module. Runtime orb widths are governed by the orb-class defaults; the fallback column documents the literal `default_orb_deg` stored alongside each aspect for tooling that needs a per-aspect override.

| Aspect | Angle (deg) | Class | Runtime orb (deg) | Declared fallback |
| --- | --- | --- | --- | --- |
| antiscia | 0.0 | mirror | 1.0 | 1.0 |
| binovile | 80.0 | harmonic | 1.0 | 1.0 |
| biquintile | 144.0 | minor | 2.0 | 2.0 |
| biseptile | 102.857 | harmonic | 1.0 | 1.0 |
| conjunction | 0.0 | major | 8.0 | 10.0 |
| contraantiscia | 180.0 | mirror | 1.0 | 1.0 |
| contraparallel | 180.0 | declination | 1.0 | 1.0 |
| fifteenth | 24.0 | harmonic | 1.0 | 1.0 |
| novile | 40.0 | harmonic | 1.0 | 1.0 |
| opposition | 180.0 | major | 8.0 | 10.0 |
| parallel | 0.0 | declination | 1.0 | 1.0 |
| quattuordecile | 25.717 | harmonic | 1.0 | 1.0 |
| quincunx | 150.0 | minor | 2.0 | 3.0 |
| quindecile | 165.0 | harmonic | 1.0 | 2.0 |
| quintile | 72.0 | minor | 2.0 | 2.0 |
| semioctile | 22.5 | minor | 2.0 | 1.0 |
| semiquintile | 36.0 | minor | 2.0 | 2.0 |
| semisextile | 30.0 | minor | 2.0 | 3.0 |
| semisquare | 45.0 | minor | 2.0 | 3.0 |
| septile | 51.428 | harmonic | 1.0 | 1.0 |
| sesquiquadrate | 135.0 | minor | 2.0 | 3.0 |
| sextile | 60.0 | major | 8.0 | 6.0 |
| square | 90.0 | major | 8.0 | 8.0 |
| tredecile | 108.0 | harmonic | 1.0 | 2.0 |
| trine | 120.0 | major | 8.0 | 8.0 |
| triseptile | 154.286 | harmonic | 1.0 | 1.0 |
| undecile | 32.717 | harmonic | 1.0 | 1.0 |
| vigintile | 18.0 | harmonic | 1.0 | 1.0 |

Notes:

- The runtime orb is derived from `VCA_RULESET.orb_class_defaults`. If an aspect class is not listed in that map the engine falls back to `default_orb_deg`.
- Declination contacts (`parallel`, `contraparallel`) share the same 1° class orb and are further bounded by the declination policy in the profile file.

## Orb policies and combustion windows

`profiles/base_profile.yaml` captures the thresholds consumed by the detectors and severity scorer:

- **Angular priority**: natal angles receive a 3° gate (`angular_priority_orb_deg`).
- **Transit body orbs (degrees)**: Sun 8, Moon 6, Mercury–Mars 6, Jupiter–Pluto 6/5, Ceres–Vesta 4, Eris/Sedna 3.
- **Fixed stars**: default longitude orb 0.333°, bright stars (<1 magnitude) tighten to 0.1667° (`fixed_star_orbs_deg`).
- **Declination aspects**: 0.5° default, Moon 0.6667° (`declination_aspect_orb_deg`).
- **Midpoints**: 1° default, 1.5° on angular pairs (`midpoint_orb_deg`).
- **Combustion**: cazimi 0.2833°, under beams 15°, combust 8° (`combustion` block).

The JSON document in `schemas/orbs_policy.json` mirrors the major aspect families and exposes profile multipliers (`standard`, `tight`, `wide`) so downstream tooling can align with the engine.

## Severity weights and dignity hooks

`profiles/base_profile.yaml` also stores per-body severity multipliers used when the detectors emit events. Selected values:

| Body | Severity weight | Notes |
| --- | --- | --- |
| Sun | 1.00 | Baseline weight for luminary contacts |
| Moon | 1.10 | Extra emphasis for rapid cycles |
| Mercury | 1.00 | Neutral |
| Venus | 0.95 | Slightly softened to avoid overstating supportive hits |
| Mars | 1.15 | Elevated because of acute triggers |
| Jupiter | 0.85 | Dialled back to avoid over-saturation |
| Saturn | 1.05 | Emphasises structural events |
| Uranus | 0.80 | Surprise events weighted modestly |
| Neptune | 0.75 | Diffuse influence |
| Pluto | 0.85 | Long-term pressure |
| Ceres | 0.60 | Supportive overlays without dominating the score |
| Pallas | 0.55 | Treated as a supplemental trigger |
| Juno | 0.55 | Same weighting as other partnership asteroids |
| Vesta | 0.55 | Keeps ritual/service themes proportional |
| Eris | 0.65 | Allows disruptive contacts without overpowering majors |
| Sedna | 0.60 | Reserved for deep background transits |

The dignity table (`profiles/dignities.csv`) lists the rulership/fall/triplicity modifiers that feed additional severity multipliers (e.g., benefic/malefic adjustments, essential dignity bonuses). Fixed-star bonuses originate from `profiles/fixed_stars.csv`, which includes longitude/declination positions, magnitudes, and default orbs for each entry.

## Domain scoring

Domain multipliers and weightings are defined in `profiles/vca_outline.json`. The helper `astroengine.core.scoring.compute_domain_factor` consumes those weights and the domain resolution emitted by `astroengine.domains.DomainResolver`. Tests in `tests/test_domain_scoring.py` and `tests/test_domains.py` assert the weighting functions behave deterministically across the supported methods (`weighted`, `top`, `softmax`).

## Validation coverage

- `tests/test_vca_ruleset.py` verifies that key aspect angles and orb lookups exposed through `astroengine.rulesets` match the table above.
- `tests/test_orbs_policy.py` loads `schemas/orbs_policy.json` via `astroengine.data.schemas.load_schema_document` and checks that the published multipliers and base orbs remain in sync with this document.
- `tests/test_vca_profile.py` exercises the profile loader to ensure aspects and orb toggles from JSON/YAML inputs survive round-tripping before detectors consume them.
- `tests/test_domain_scoring.py` and `tests/test_domains.py` confirm that the domain weighting utilities respect the multipliers distributed in `profiles/vca_outline.json` and the severity modifiers above.

Keeping this specification aligned with the referenced files ensures future changes to the aspect canon or severity tables remain auditable and no module/submodule/channel entries are lost during edits.
