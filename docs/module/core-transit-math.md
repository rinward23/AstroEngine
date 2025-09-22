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

## Data provenance and lineage

Every numeric value in the Venus Cycle Analytics (VCA) ruleset is traceable to a concrete upstream dataset. The repository keeps
Solar Fire 9 exports, Swiss Ephemeris state vectors, and AstroEngine’s curated CSV/JSON profiles under version control so no
module relies on synthetic placeholders:

- **Solar Fire aspect templates** underpin the canonical angles and orb defaults. The exported catalogue is normalised into
  `astroengine/modules/vca/rulesets.py`, and the profile multipliers from Solar Fire’s `DEFAULT.ASF` preset are captured in
  `schemas/orbs_policy.json`.
- **Swiss Ephemeris (DE441)** calculations are used to verify angular velocity and applying/separating status whenever detectors
  are prototyped. The provenance block in `profiles/base_profile.yaml` records the exact ephemeris build that was referenced when
  calibrating the combustion and lunation gates.
- **Solar Fire dignity/fixed star tables** are collapsed into `profiles/dignities.csv` and `profiles/fixed_stars.csv`. Their
  checksums and revision dates live alongside the files so governance can confirm the shipped data has not drifted.

When additional Solar Fire or third-party datasets are introduced, index them under the `profiles/` directory, append a
`source`/`provenance` column, and log the update in `docs/governance/data_revision_policy.md`. The runtime refuses to load assets
that are missing provenance metadata, ensuring the module hierarchy always resolves to verifiable inputs.

## Aspect canon

`VCA_RULESET` enumerates every aspect supported by the default Venus Cycle Analytics module. Runtime orb widths are governed by the orb-class defaults; the fallback column documents the literal `default_orb_deg` stored alongside each aspect for tooling that needs a per-aspect override.

| Aspect | Angle (deg) | Class | Runtime orb (deg) | Declared fallback | Provenance |
| --- | --- | --- | --- | --- | --- |
| antiscia | 0.0 | mirror | 1.0 | 1.0 | Solar Fire declination pack (`DEFAULT.ASF`) |
| binovile | 80.0 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| biquintile | 144.0 | minor | 2.0 | 2.0 | Solar Fire harmonic extensions |
| biseptile | 102.857 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| conjunction | 0.0 | major | 8.0 | 10.0 | Solar Fire default aspect set |
| contraantiscia | 180.0 | mirror | 1.0 | 1.0 | Solar Fire declination pack (`DEFAULT.ASF`) |
| contraparallel | 180.0 | declination | 1.0 | 1.0 | Solar Fire declination pack (`DEFAULT.ASF`) |
| fifteenth | 24.0 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| novile | 40.0 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| opposition | 180.0 | major | 8.0 | 10.0 | Solar Fire default aspect set |
| parallel | 0.0 | declination | 1.0 | 1.0 | Solar Fire declination pack (`DEFAULT.ASF`) |
| quattuordecile | 25.717 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| quincunx | 150.0 | minor | 2.0 | 3.0 | Solar Fire optional aspect pack |
| quindecile | 165.0 | harmonic | 1.0 | 2.0 | Noel Tyl quindecile catalogue, verified in Solar Fire |
| quintile | 72.0 | minor | 2.0 | 2.0 | Solar Fire harmonic extensions |
| semioctile | 22.5 | minor | 2.0 | 1.0 | Solar Fire minor aspect set |
| semiquintile | 36.0 | minor | 2.0 | 2.0 | Solar Fire harmonic extensions |
| semisextile | 30.0 | minor | 2.0 | 3.0 | Solar Fire minor aspect set |
| semisquare | 45.0 | minor | 2.0 | 3.0 | Solar Fire minor aspect set |
| septile | 51.428 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| sesquiquadrate | 135.0 | minor | 2.0 | 3.0 | Solar Fire minor aspect set |
| sextile | 60.0 | major | 8.0 | 6.0 | Solar Fire default aspect set |
| square | 90.0 | major | 8.0 | 8.0 | Solar Fire default aspect set |
| tredecile | 108.0 | harmonic | 1.0 | 2.0 | Solar Fire harmonic extensions |
| trine | 120.0 | major | 8.0 | 8.0 | Solar Fire default aspect set |
| triseptile | 154.286 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| undecile | 32.717 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |
| vigintile | 18.0 | harmonic | 1.0 | 1.0 | Solar Fire harmonic extensions |

Notes:

- The runtime orb is derived from `VCA_RULESET.orb_class_defaults`. If an aspect class is not listed in that map the engine falls back to `default_orb_deg`.
- Declination contacts (`parallel`, `contraparallel`) use the declination orb policy in `profiles/base_profile.yaml` (0°30′ default, 0°40′ when the Moon is involved) on top of the shared 1° class orb.

## Orb policies and combustion windows

`profiles/base_profile.yaml` captures the thresholds consumed by the detectors and severity scorer:

- **Angular priority**: natal angles receive a 3° gate (`angular_priority_orb_deg`).
- **Transit body orbs (degrees)**: Sun 8, Moon 6, Mercury–Mars 6, Jupiter–Pluto 6/5, Ceres–Vesta 4, Eris/Sedna 3.
- **Fixed stars**: default longitude orb 0.333°, bright stars (<1 magnitude) tighten to 0.1667° (`fixed_star_orbs_deg`).
- **Declination aspects**: 0.5° default, Moon 0.6667° with per-type overrides under `declination_aspect_orb_deg`.
- **Antiscia mirrors**: 1.5° default, 2.5° when a natal angle participates; axis defaults to Cancer–Capricorn with Aries–Libra available via `feature_flags.antiscia.axis`.
- **Midpoints**: 1° default, 1.5° on angular pairs (`midpoint_orb_deg`).
- **Combustion**: cazimi 0.2833°, under beams 15°, combust 8° (`combustion` block).

The JSON document in `schemas/orbs_policy.json` mirrors the major aspect families and exposes profile multipliers (`standard`, `tight`, `wide`) so downstream tooling can align with the engine. Keep the schema entry in sync with this document and note revisions in [`docs/governance/data_revision_policy.md`](../governance/data_revision_policy.md).

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

The dignity table (`profiles/dignities.csv`) lists the rulership/fall/triplicity modifiers that feed additional severity multipliers (e.g., benefic/malefic adjustments, essential dignity bonuses). Each record contains explicit source citations (Solar Fire export IDs and classical text references) and the table is indexed by `(planet, sign)` so profile loaders can join deterministically. Fixed-star bonuses originate from `profiles/fixed_stars.csv`, which includes longitude/declination positions, magnitudes, default orbs, and source manifest hashes for the FK6 reduction bundled with Solar Fire.

## Domain scoring

Domain multipliers and weightings are defined in `profiles/vca_outline.json`. The helper `astroengine.core.scoring.compute_domain_factor` consumes those weights and the domain resolution emitted by `astroengine.domains.DomainResolver`. Tests in `tests/test_domain_scoring.py` and `tests/test_domains.py` assert the weighting functions behave deterministically across the supported methods (`weighted`, `top`, `softmax`).

## Validation coverage

- `tests/test_vca_ruleset.py` verifies that key aspect angles and orb lookups exposed through `astroengine.rulesets` match the table above.
- `tests/test_orbs_policy.py` loads `schemas/orbs_policy.json` via `astroengine.data.schemas.load_schema_document` and checks that the published multipliers and base orbs remain in sync with this document.
- `tests/test_vca_profile.py` exercises the profile loader to ensure aspects and orb toggles from JSON/YAML inputs survive round-tripping before detectors consume them.
- `tests/test_domain_scoring.py` and `tests/test_domains.py` confirm that the domain weighting utilities respect the multipliers distributed in `profiles/vca_outline.json` and the severity modifiers above.

## Indexing and determinism guarantees

- `profiles/vca_outline.json` exposes the module → submodule → channel → subchannel hierarchy used by the runtime registry. Each
  node carries a `registry_path` so documentation updates cannot orphan modules.
- The `astroengine.modules.registry` component stores metadata for every rule or lookup. Populate that metadata with provenance
  URIs whenever detectors are added to the registry (e.g., `sf9://transits_2023.sf#row=5821`) so downstream audit tooling can
  trace an emitted event back to primary data.
- Large Solar Fire exports should be indexed before ingestion. Store the index either as SQLite (`*.sqlite`) or as adjacency
  metadata in `profiles/` and record the build command in the revision log. The runtime only accepts indexed datasets to prevent
  slow sequential scans during live transit monitoring.

Keeping this specification aligned with the referenced files ensures future changes to the aspect canon or severity tables remain
auditable and no module/submodule/channel entries are lost during edits. Every addition must cite real data and update the
corresponding provenance blocks so user-facing output always reflects verifiable sources.
