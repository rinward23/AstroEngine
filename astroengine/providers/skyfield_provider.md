```AUTO-GEN[providers.skyfield]
GOAL
  - Define the reference Skyfield ephemeris provider implementing the `EphemerisProvider` protocol with deterministic caching, DE440s support, and telemetry hooks.

INITIALIZATION FLOW
  1. Validate extras: ensure `skyfield`, `jplephem`, `numpy`, `astropy`, `tzdata` (fallback) are installed. Abort with `ProviderError` (error_code=`missing_dependency`).
  2. Resolve cache directory: default `${ASTROENGINE_CACHE}/skyfield/de440s`; support override via profile flag `providers.skyfield.cache_path`. Enforce path whitelist to avoid traversals.
  3. Invoke `ephem pull` helper:
        a. Check existing DE440s files (binary + checksum). If missing/stale, download from NASA/JPL using HTTPS with retry policy (3 attempts, exponential backoff) and SHA-256 verification.
        b. Record `CacheInfo` (path, checksum, generated_at, status).
  4. Construct Skyfield `Loader` pinned to cache directory and instantiate `Timescale` with timezone-safe settings (UTC + TT conversions using `astropy.time`).
  5. Preload commonly-used bodies: Sun, Moon, Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, lunar node approximations, selected asteroids (Ceres, Pallas, Juno, Vesta) when extras `minor_planets` present.

QUERY HANDLING
  - `prime_cache`: compute sampling cadence per body class (inners ≤6h, outers ≤24h, Moon ≤1h) and prefetch times using vectorized `timescale.utc`. Store deterministic list of sample timestamps.
  - `query`: accept arbitrary timestamps; convert to Skyfield `Time` objects; fetch geocentric positions via `.at(time).observe(body).apparent()`; compute ecliptic longitude/latitude (true ecliptic of date) using `astropy.coordinates`. Include light-time correction metadata.
  - `query_window`: generate uniform times; reuse `prime_cache` data when available to avoid duplicate work; ensure returned vectors sorted chronologically.
  - Declination/out-of-bounds: compute from equatorial coordinates; attach `declination_deg` field.
  - Provide `data_provenance`: {`ephemeris`: `de440s`, `timescale`: `skyfield`, `light_time`: bool, `frame`: requested frame, `source_checksum`: SHA-256}.

DETERMINISM & CACHING
  - All numpy arrays must be coerced to Python floats (rounded to 1e-9) before serialization to avoid platform drift.
  - Cache metadata stored in JSON alongside ephemeris file; include `sha256`, `download_url`, `downloaded_at`, `skyfield_version`, `astroengine_version`.
  - Determinism hash inputs must include: timestamps (ISO8601), body_id, frame, computed longitude/latitude, declination, speed, cache checksum.

TELEMETRY
  - Structured logs for each query: {`module`: `providers.skyfield`, `call`: `query|query_window|prime_cache`, `bodies`, `count`, `cache_status`, `duration_ms`, `errors` (if any)}.
  - Metrics counters: `astroengine_provider_queries_total` (labels: provider_id, call), `astroengine_provider_cache_hits_total`, `astroengine_provider_failures_total` (labels include `error_code`).

ERROR HANDLING
  - Missing cache/failed checksum → `ProviderError` with `error_code=cache_invalid`, `retriable=True`.
  - Network failure after retries → `ProviderError` with `error_code=download_failed`, `retriable=True`.
  - Unsupported body/frame → `ProviderError` with `error_code=unsupported_target`, `retriable=False`.

CONFORMANCE TESTS
  - Compare positions for canonical timestamps vs Swiss Ephemeris within tolerances: inner planets ≤0.5 arcsec, outers ≤1.0 arcsec, Moon ≤2.0 arcsec.
  - Determinism test: run `query_window` twice with identical inputs; ensure determinism hash identical.
  - Cache reuse test: delete in-memory caches, re-run `prime_cache`, confirm `CacheInfo.status`=`WARM` when files unchanged.
```
