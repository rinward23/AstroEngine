<!-- >>> AUTO-GEN BEGIN: Harmonic Charts v1.0 (instructions) -->
Definition
- The **N-th harmonic chart** transforms longitudes as λ_N = (N × λ_base) mod 360°, applied to all bodies/points in a source chart (natal or progressed). Aspects in base become **conjunctions** in the N-th harmonic.

Profiles
- Default OFF; enable per N for H5/H7/H9/H11. Provide orbit/visibility toggles and restrict to conjunctions/oppositions within the harmonic chart (optional extra aspects).

Ruleset Hooks
- Allow scanning transits **to** harmonic chart points (e.g., transiting outer to natal 5th harmonic Venus), or analyze harmonic chart patterns internally.

Outputs
- Attach `chart_kind: harmonic:N` to derived outputs; record base chart metadata and N used.

Acceptance
- Verify λ_N formula on sample points; quintile in base chart manifests as conjunction in H5, etc.
<!-- >>> AUTO-GEN END: Harmonic Charts v1.0 (instructions) -->
