# VCA Outline → AstroEngine Mapping (ops guide)

- **Bodies** → `profiles/vca_outline.json.bodies` (`include`, `optional_groups`, `fixed_stars`).
- **Aspects** (Major/Minor/Harmonics, Declination, Antiscia) → `aspects`.
- **Orbs** → `orbs` with degrees per angle; engine reads via `ctx['orbs']`.
- **Domains (Mind/Body/Spirit)** → `domain` (weights, scorer, temperature, profile key).
- **Feature Flags** (declination/antiscia/harmonics/fixed stars) → `flags`.
- **Modules** (EARTH/AIR/FIRE/WATER)** → recorded for tagging; no runtime effect yet.

## How it flows
1. `--profile-file profiles/vca_outline.json` (CLI) → load.
2. `apply_profile_if_any(ctx, profile)` merges keys into engine context.
3. Detectors & orb logic read `ctx['aspects']`, `ctx['orbs']`, `ctx['flags']`.
4. Domain severity uses `ctx['domain_*']` (see CP10/CP11 v1.1).

## Notes
- Fixed stars and large TNO/asteroid sets are **disabled by default**; enable only when ephemerides are available.
- Orbs reflect VCA ranges (midpoint values). Adjust per user profile as needed.
