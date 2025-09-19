```AUTO-GEN[transit.ingresses]
OVERVIEW
  - Detect sign changes for enabled bodies, ensuring deterministic capture of ingress moments and natal gating when required.
  - Channel hierarchy: module `transit.ingresses` → channel `ingresses` → subchannels `solar`, `lunar`, `inner`, `outer`, `minor`, `dwarf` keyed by body class.

DATA REQUIREMENTS
  - Geocentric ecliptic longitude samples with sign index (0–11) per timestamp.
  - Provider metadata for interpolation (Hermite/lagrange) and timezone-safe timescales.
  - Natal reference longitudes and angular positions; profile gating tables for angle proximity thresholds.

BODY POLICY
  - Always include Sun, Mars, Jupiter, Saturn across entire timeline.
  - Mercury, Venus: include when profile `ingresses.inner_mode = always` OR when within ≤3° of natal angles flagged for ingress priority (ASC, MC, IC, DSC, Vertex/Antivertex, Fortune/Spirit when toggled).
  - Moon: optional; include when profile `ingresses.include_moon = true` with gating by ≤3° to natal angles or luminaries.
  - Outer planets (Uranus, Neptune, Pluto) and dwarfs (Eris, Sedna): include when profile toggles enable them or natal proximity ≤2°.
  - Minor planets (Ceres, Pallas, Juno, Vesta): include when profile `minor_planets.ingresses = true` and severity weight > 0.

DETECTION FLOW
  1. For each body, compare consecutive longitude samples; detect sign index change (mod 30° crossing).
  2. Use deterministic root finding to solve for longitude = boundary (k×30°); tolerance ≤5 minutes (UTC).
  3. Derive event metadata: `ingress_sign`, `sign_from`, `sign_to`, `degree_in_sign` (0°), `house`, `motion` (`direct`/`retrograde`), `speed_deg_per_day`, `body_class`.
  4. Apply natal gating for conditional bodies; compute `nearest_natal` (body/angle id, separation deg/min) and attach to event.
  5. Evaluate severity: base severity from profile; ×1.2 when ingress hits domicile/exaltation sign for body; ×0.85 when in detriment/fall; ×1.1 when aligning with profected house ruler.
  6. Log whether ingress occurs during retrograde; attach `retrograde_flag` and tie-in to station module for cross-validation.

OUTPUT FIELDS
  - `timestamp`, `body_id`, `ingress_sign`, `previous_sign`, `motion`, `retrograde_flag`, `orb_to_natal`, `natal_ref`, `severity`, `severity_modifiers`, `profile_flags`, `provider_samples`, `determinism_inputs`.

VALIDATION
  - Schema: `schemas/events/transit_ingress.schema.json`.
  - Determinism: same inputs must produce identical timestamps and severity; include sign change boundary IDs in hash inputs.
  - Cross-check: ensure each ingress is flanked by samples in old/new sign and that interpolation solution lies within bounds.
  - Logging: JSON with `body_id`, `ingress_sign`, `timestamp`, `nearest_natal`, `severity`, `hash_fragment`.
```
