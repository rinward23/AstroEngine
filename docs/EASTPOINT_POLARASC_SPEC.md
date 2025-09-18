<!-- >>> AUTO-GEN BEGIN: East Point & Polar Ascendant v1.0 (instructions) -->
Definitions
- **East Point (Equatorial Ascendant)**: the ecliptic point rising **due East** (azimuth = 90°) for the observer at the moment; compute via intersection of ecliptic with prime vertical at azimuth 90°.
- **Polar Ascendant**: ecliptic intersection with the **prime vertical** at the meridian (north/south) for high latitudes; used as an alternate ascendant.

Provider Requirements
- Provide EP and PA longitudes given (t, lat, lon); document the frame conversions and refraction assumptions (none by default).

Aspects & Orbs
- Treat EP/PA as **angles**: use angle-tight orbs (≤3° majors, ≤1.5° minors).

Gating & Outputs
- Include contacts to transiting personals/outers; flag `is_angle_variant = true`, `angle_kind = EP|PA`.

Acceptance
- Cross-check EP vs known software for sample latitudes (±0.5° tolerance); PA available and stable at high latitudes.
<!-- >>> AUTO-GEN END: East Point & Polar Ascendant v1.0 (instructions) -->
