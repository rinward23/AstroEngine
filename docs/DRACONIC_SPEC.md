<!-- >>> AUTO-GEN BEGIN: Draconic Zodiac v1.0 (instructions) -->
Definition
- Draconic longitude λ_d = (λ_tropical − Ω_NN) mod 360°, where Ω_NN is chosen (Mean Node default; profile can select True Node).
- Property: North Node is always 0° Aries in draconic.

Outputs
- Provide alternate longitudes for bodies/points; export field: `coord.draconic.lon_deg`.
- Profiles: `draconic.enabled` (default false), `draconic.node = mean|true`.

Acceptance
- Invariant: Node at 0° Aries; consistency check λ_tropical = (λ_d + Ω_NN) mod 360.
- Example test: if tropical Sun = Ω_NN then draconic Sun = 0° Aries.
<!-- >>> AUTO-GEN END: Draconic Zodiac v1.0 (instructions) -->
