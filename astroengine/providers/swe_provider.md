```AUTO-GEN[providers.swe]
GOAL
  - Scaffold an optional Swiss Ephemeris provider (`pyswisseph`) that mirrors the Skyfield API for parity testing while respecting licensing constraints.

LICENSE & DISTRIBUTION
  - `pyswisseph` is GPL; package behind `astroengine[swe]` extra with clear NOTICE file linking to Swiss Ephemeris license.
  - Document that commercial distribution requires contacting Astrodienst; default build disables SWE provider unless user opts in.

INITIALIZATION STEPS
  1. Validate dependency availability (`pyswisseph`, `numpy`). If missing, raise `ProviderError` (`error_code=missing_dependency`, `retriable=False`).
  2. Require explicit `swe_ephemeris_path` config (profile flag or env var). Disallow silent downloads.
  3. Load Swiss Ephemeris data via `astroengine.engine.ephe_runtime.init_ephe()`; compute checksum of ephemeris directory and store in `CacheInfo`.
  4. Configure delta-T model (default `swe.DELTAT_DEFAULT`); allow override via profile `providers.swe.delta_t`.

QUERY IMPLEMENTATION
  - `prime_cache`: verify ephemeris files exist for requested range; call `swe.set_topo` when geographic context required (for house calculations) but keep transit queries geocentric by default.
  - `query`: convert timestamps to Julian day (`swe.julday`), call `swe.calc_ut` for body IDs mapped from AstroEngine canonical names; gather longitude, latitude, distance, speed. Combine the `init_ephe()` base flag with `FLG_SPEED | FLG_EQUATORIAL`. Convert equatorial coords to RA/Dec.
  - `query_window`: iterate across cadence; maintain deterministic ordering; store `data_provenance` referencing Swiss ephemeris file names and versions.
  - Ensure floating-point outputs rounded to 1e-9 precision to maintain parity with Skyfield determinism tests.

FEATURE SUPPORT
  - Bodies: Sun → Pluto, Moon, mean/true nodes, Chiron (optional), minor planets when element files present; declare support list in `ProviderMetadata`.
  - Declination & right ascension natively available; ensure antiscia calculations align with Skyfield outputs within tolerance.
  - Light-time corrections configurable via profile flag (default ON).

PARITY & TESTING
  - Provide conformance suite comparing SWE vs Skyfield across 50 timestamps (per body). Tolerances: inners ≤0.5 arcsec, outers ≤1.0 arcsec, Moon ≤2.0 arcsec.
  - Determinism tests identical to Skyfield provider.
  - Document how to disable SWE provider at runtime (profile `providers.swe.enabled = false`).

SECURITY & LOGGING
  - Enforce path whitelist for ephemeris directory; refuse relative paths escaping allowed roots.
  - Log queries with structured metadata similar to Skyfield provider; include `ephemeris_version` and `delta_t_model`.
  - On errors, raise `ProviderError` with `error_code` from set {`missing_dependency`, `invalid_path`, `unsupported_target`, `compute_failure`}.
```
