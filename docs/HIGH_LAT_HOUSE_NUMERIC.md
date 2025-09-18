<!-- >>> AUTO-GEN BEGIN: High-Latitude Fallbacks v1.0 (instructions) -->
Rules
- If Placidus/Topocentric fail (non‑real cusps) above |φ| ≥ 66°: fallback → Whole Sign; log `house_fallback = true` with `fallback_system = Whole Sign`.
- Warning threshold: |φ| ≥ 61° emit advisory even if computation succeeds.

Acceptance
- Tests at 70°N and 75°S verify fallback triggers; outputs include warning flag; no crashes.
<!-- >>> AUTO-GEN END: High-Latitude Fallbacks v1.0 (instructions) -->
