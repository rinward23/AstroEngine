<!-- >>> AUTO-GEN BEGIN: Providers Spec v1.0 (instructions) -->
Purpose: define a plugin contract for ephemeris/providers (Skyfield default, SWE optional, Mock for tests) and discovery via entry points.

Contract (capabilities):
- ecliptic_state(t_iso, topocentric: bool, lat, lon, elev_m) -> {body: {lon_deg, lon_speed_deg_per_day, decl_deg?}}
- lunation(type: new|full, window) -> list[exact_iso]
- eclipse(window) -> list[{exact_iso, kind: solar|lunar, saros?}]
- station(body, window) -> list[{exact_iso, kind: retro|direct}]
- houses(dt_iso, lat, lon, system) -> {ASC, MC, IC, DSC, cusps[1..12]}
- ayanamsha(name) -> offset_deg
- ephemeris_info() -> {name, version, checksum}

Discovery:
- entry point group `astroengine.providers` with names: `skyfield`, `swe`, `mock`.

Profiles & options:
- Parameters: house_system, ayanamsha, observatory (lat/lon/elev), de_set.
- Defaults: Whole Sign houses; Tropical zodiac; de440s; geocentric/topocentric toggle.

Acceptance:
- Cross-backend parity for Sun–Pluto longitudes within arcsecond bands.
- House cusp checks for common systems.
- Lunation/eclipse exacts match published tables within minutes.
<!-- >>> AUTO-GEN END: Providers Spec v1.0 (instructions) -->
