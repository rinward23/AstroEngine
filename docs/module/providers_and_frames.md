# Providers & Frames Contract

- **Module**: `providers`
- **Maintainer**: Ephemeris Guild
- **Source artifacts**:
  - `astroengine/providers/__init__.py` (protocol definitions used by plugins).
  - `astroengine/providers/skyfield_provider.md` and `astroengine/providers/swe_provider.md` (design notes for the bundled providers).
  - `profiles/base_profile.yaml` (`providers.*` and cadence settings).
  - `docs/module/event-detectors/overview.md` (detectors that depend on provider outputs).

AstroEngine resolves ephemeris data through provider plugins that implement the `EphemerisProvider` protocol. The goal of this document is to record the contract expected by the runtime so that future providers remain deterministic, expose provenance, and keep the module/submodule/channel hierarchy intact.

## Provider protocol summary

`astroengine/providers/__init__.py` defines the following structures:

- **`ProviderMetadata`** — declares `provider_id`, `version`, supported bodies, supported frames, declination/light-time support, cache layout, and any extras required for installation.
- **`CacheInfo` / `CacheStatus`** — track ephemeris cache provenance (path, checksum, generated timestamp, warm/cold/stale/invalid state).
- **`EphemerisVector`** — holds the deterministic output of a provider query: position/velocity vectors, ecliptic longitude/latitude, right ascension/declination, distance (AU), longitudinal speed, and a provenance map.
- **`EphemerisBatch`** — wraps a sequence of vectors with cache metadata and determinism inputs.
- **`EphemerisProvider`** — protocol with methods `configure`, `prime_cache`, `query`, `query_window`, and `close`. All implementations must raise `ProviderError` with `provider_id`, `error_code`, and `retriable` fields so callers can react consistently.

## Bundled provider plans

Two provider designs ship in Markdown form to document expected behaviour:

- **Skyfield provider** (`astroengine/providers/skyfield_provider.md`): details cache warming for DE440s files, cadence policies (inners ≤6h, outers ≤24h, Moon 1h), light-time handling, and deterministic logging requirements. The notes also specify the metrics/events providers should emit.
- **Swiss Ephemeris provider** (`astroengine/providers/swe_provider.md`): outlines licensing considerations, dependency checks, delta-T configuration, and parity expectations relative to Skyfield.

Although the implementations are not yet checked in, the documentation establishes the provenance requirements and failure taxonomy that runtime code must follow. Any provider added to the registry must cite its design document and update this file.

## Coordinate frames and cadences

Profiles reference providers through the following keys in `profiles/base_profile.yaml`:

- `providers.default` selects the primary plugin (`skyfield` by default).
- `providers.skyfield.cache_path` documents the expected ephemeris cache location (`${ASTROENGINE_CACHE}/skyfield/de440s`).
- `providers.swe.enabled` and `providers.swe.delta_t` illustrate how optional providers expose toggles.
- `providers.*.cadence_hours` define recommended sampling cadences by body class (`inner`, `outer`, `moon`, `minor`). Detectors should inherit these settings to keep the pipeline deterministic.
- Cadence and cache settings must be cross-checked against Solar Fire export intervals; record any deviations in the provenance log so comparisons remain valid.

House system and ayanamsha preferences are stored under `feature_flags.house_system` and `feature_flags.sidereal` in the same profile file. Detectors that rely on relocation/house calculations must combine those flags with provider metadata to select the correct frame.

## Provenance & testing expectations

- Provider implementations must surface cache checksums through `CacheInfo` and attach `data_provenance` dictionaries to each `EphemerisVector`.
- Structured logging should include `provider_id`, call type (`query`, `query_window`, `prime_cache`), cache status, and timing information as described in the Skyfield design notes.
- Once implementations land, parity tests comparing providers (Skyfield vs. Swiss Ephemeris) should be added under `tests/` to guarantee positional differences stay within documented tolerances. Include Solar Fire export comparisons for representative charts and archive the export checksums.
- Environment validation via `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` should precede provider parity runs to confirm dependency versions.
- Record revisions to provider configurations and documentation according to `docs/governance/data_revision_policy.md` so provenance remains auditable.
- Providers must never fabricate values. When a dataset is unavailable (e.g., Solar Fire export missing), raise a provenance error rather than falling back to synthetic numbers.

Documenting the provider contract here ensures that future plugins remain compatible with the reworked environment while protecting the module hierarchy from accidental drift.
