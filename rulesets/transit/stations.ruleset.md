```AUTO-GEN[transit.stations]
OVERVIEW
  - Detect retrograde and direct stations for enabled bodies with deterministic interpolation and gating rules that enforce natal proximity policies.
  - Channel hierarchy: module `transit.stations` → channel `stations` → subchannels `retrograde_station`, `direct_station`.

DATA SOURCES
  - Ephemeris samples at ≤6h cadence (inner bodies) and ≤24h (outer bodies); include geocentric longitude, latitude, speed in longitude, and declination.
  - Natal reference positions and angular longitudes for the birth chart; include angles (ASC, MC, IC, DSC), Vertex/Antivertex, Fortune/Spirit when toggled.
  - Profile tables specifying orb thresholds, severity multipliers, body enablement flags, and natal gating toggles.

BODY SCOPE
  - Always scan: Sun (for cazimi/combust checks), Moon, Mercury, Venus, Mars.
  - Conditional: Jupiter, Saturn, Uranus, Neptune, Pluto when within ≤2° of any natal body/angle flagged as `angular_priority` or when profile `stations.outer_always_on = true`.
  - Optional minors: Ceres, Pallas, Juno, Vesta when profile `minor_planets.enabled = true` and `minor_planets.stations = true`.
  - Optional dwarfs: Eris, Sedna when profile toggles enable them and provider declares precision support.

DETECTION LOGIC
  1. For each body, evaluate sign of longitudinal speed across consecutive ephemeris samples; identify zero crossings via Hermite interpolation or bracketing search (≤2h tolerance).
  2. Confirm station timestamp by solving for speed = 0 using deterministic root finder (e.g., Brent) seeded with monotonic interval.
  3. Compute event metadata: body_id, station_kind (`retrograde` when speed sign changes +→−, `direct` when −→+), ecliptic longitude, sign, house (per selected system), declination, geocentric distance, motion classification (`inner`, `outer`, `minor`, `dwarf`).
  4. Evaluate natal gating:
        a. Compute minimum orb to natal bodies/angles flagged for stations (per profile `stations.natal_gate_orb_deg`).
        b. Accept event if body in always-on list OR orb ≤ threshold OR profile override forces inclusion.
        c. Attach `natal_crosscheck`: nearest body/angle id, separation degrees, separation minutes, orb flag.
  5. Apply modifiers: combust/under-beams/cazimi, out-of-bounds, benefic/malefic severity adjustments from profile tables.

SEVERITY MODEL
  - Base severity: use per-body severity weight from profile (e.g., Mercury 1.0, Venus 0.9, Mars 1.1, Jupiter 0.8, Saturn 1.0, outer/dwarf as configured).
  - Increase severity ×1.25 when orb ≤ natal angle threshold; ×1.15 when hitting natal ruler/profected lord.
  - Decrease severity ×0.85 when combust; ×0.9 when out-of-bounds disabled; ×0.75 when body flagged as minor and profile `minor_planets.weight = light`.
  - Document each adjustment with `severity_modifiers` array: {source, value, rationale}.

OUTPUT FIELDS
  - `timestamp` (UTC, ISO8601), `body_id`, `station_kind`, `sign`, `degree`, `orb_deg`, `orb_arcmin`, `natal_ref`, `severity`, `severity_modifiers`, `profile_flags`, `provider_samples` (list of timestamps/ids), `determinism_inputs` (sorted field list).

VALIDATION & TEST HOOKS
  - Schema: `schemas/events/transit_station.schema.json`.
  - Determinism: rerun detection with same inputs; hashed payload must match.
  - Property tests: ensure station timestamp falls within interpolation bounds and preceding/following samples have opposite speed signs.
  - Logging: emit JSON entries with `event_id`, `body_id`, `station_kind`, `orb`, `nearest_natal`, `severity`, `hash_fragment`.
```
