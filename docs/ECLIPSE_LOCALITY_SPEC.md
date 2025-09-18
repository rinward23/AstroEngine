<!-- >>> AUTO-GEN BEGIN: Eclipse Locality v1.0 (instructions) -->
Scope
- Compute ground path (central line, umbra/penumbra) using Besselian elements for solar eclipses; great‑circle proximity for lunar.

Inputs
- Observer lat/lon (optional); eclipse catalog (provider) returning exacts + Besselian coefficients or precomputed paths.

Rules
- Distance‑to‑centerline weighting: severity_locality = clamp(1 − d/R, 0, 1) where R is penumbral radius at closest approach.
- Time window: boost influences ±48h around local maximum; decay outside.

Outputs
- Add fields: `eclipse.local_distance_km`, `eclipse.path_class` (total/annular/partial), `locality_weight`.

Acceptance
- Sample eclipse (e.g., 2024‑04‑08) distances reproduce within ±50 km against NASA/USNO data.
<!-- >>> AUTO-GEN END: Eclipse Locality v1.0 (instructions) -->
