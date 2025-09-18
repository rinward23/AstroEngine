```AUTO-GEN[transit.lunations]
OVERVIEW
  - Emit lunation events (new, first quarter, full, last quarter) and eclipses with deterministic detection, severity weighting, and natal gating as per profile controls.
  - Channel hierarchy: module `transit.lunations` → channel `lunations` → subchannels `new_moon`, `first_quarter`, `full_moon`, `last_quarter`, `solar_eclipse`, `lunar_eclipse`.

DATA REQUIREMENTS
  - Sun and Moon geocentric ecliptic longitudes and latitudes sampled ≤1h cadence; include declination and distance for parallax corrections.
  - Node longitudes for eclipse gating; Saros catalog references when available for provenance.
  - Natal luminary/angle positions and `lunations` profile table (orb thresholds, severity multipliers, eclipse gating toggles).

DETECTION LOGIC
  1. Compute synodic phase angle Δλ = λ_sun − λ_moon; detect zero crossings (new moon) and 180° crossings (full moon) via root solving. Quarter phases via Δλ = ±90°.
  2. Timestamp accuracy requirement ≤2 minutes UTC; store interpolation inputs (timestamps, longitudes) for provenance.
  3. Determine lunation type from solved Δλ value.
  4. Evaluate eclipse potential for new/full lunations:
        a. Compute absolute ecliptic latitude of Moon at event; require ≤ profile `eclipse_lat_deg` (default 1.5°).
        b. Compute separation from nodes; require ≤ profile `eclipse_node_orb_deg` (default 1.0°).
        c. Mark `eclipse_flag = true` and classify as solar (new moon) or lunar (full moon) when thresholds satisfied.
  5. Cross-check natal proximity: compute orb to natal Sun, Moon, ASC, MC, IC, DSC, Vertex, Fortune/Spirit; attach nearest reference and orb.
  6. Detect angular emphasis: if orb ≤ profile `lunations.angular_orb_deg` (default 3°) to any angle/luminary, tag `angular_priority = true`.

SEVERITY MODEL
  - Base severity values: new/full = 1.0, quarters = 0.7, eclipses = 1.4 baseline.
  - Apply modifiers:
        * ×1.2 when angular priority true.
        * ×1.2 when lunation aligns with profected lord/house.
        * ×0.9 when Moon out-of-bounds disabled; ×1.05 when OOB present and profile `lunations.oob_bonus = true`.
        * ×0.85 when in detriment/fall sign for luminary per dignities table.
        * Additional ×1.1 when within ≤1° of natal luminary; ×1.3 for eclipses within ≤1° of natal luminary/angle (hard requirement for emission per acceptance).
  - Document modifiers in `severity_modifiers` with {source_flag, multiplier, justification}.

OUTPUT FIELDS
  - `timestamp`, `lunation_type`, `eclipse_flag`, `eclipse_class` (partial/total computed from magnitude when available), `sun_longitude`, `moon_longitude`, `phase_angle`, `orb_deg`, `orb_arcmin`, `natal_ref`, `angular_priority`, `severity`, `severity_modifiers`, `profile_flags`, `provider_samples`, `determinism_inputs`.

VALIDATION & TESTS
  - Schema: `schemas/events/transit_lunation.schema.json`.
  - Determinism: repeated runs with same ephemeris inputs must produce identical timestamps/severity/hashes.
  - Property tests: ensure Δλ evolution crosses the expected angle within buffer window; verify solar eclipses occur when Moon near node and near new moon.
  - Logging: JSON entries with `lunation_type`, `timestamp`, `eclipse_flag`, `nearest_natal`, `severity`, `hash_fragment`, `provider_samples`.

DEPENDENCIES & CROSS-LINKS
  - Requires provider support for high-cadence sampling; enforce fetch of Sun/Moon positions + node data with caching.
  - Cross-reference fixed star table for magnitude adjustments when Moon or Sun conjoins bright star within ≤0°20′ (profile toggle `fixed_stars.lunation_bonus`).
  - Link with returns module to flag lunations within ±48h of solar/lunar returns for severity ×1.1 (profile `returns.lunation_boost`).
```
