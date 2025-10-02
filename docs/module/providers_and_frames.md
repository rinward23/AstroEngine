# Providers & Frames Contract

- **Module**: `providers`
- **Maintainer**: Ephemeris Guild
- **Source artifacts**:
  - `astroengine/providers/__init__.py` (protocol definitions used by plugins).
  - `astroengine/providers/skyfield_provider.md` and `astroengine/providers/swe_provider.md` (design notes for the bundled providers).
  - `profiles/base_profile.yaml` (`providers.*` and cadence settings).
  - `docs/module/event-detectors/overview.md` (detectors that depend on provider outputs).

AstroEngine resolves ephemeris data through provider plugins that implement the `EphemerisProvider` protocol. The goal of this document is to record the contract expected by the runtime so that future providers remain deterministic, expose provenance, and keep the module/submodule/channel hierarchy intact.

## Registry mapping

The default registry exports the following provider paths:

- `providers.ephemeris.plugins.swiss_ephemeris`
- `providers.ephemeris.plugins.skyfield`
- `providers.cadence.profiles.default`
- `providers.frames.preferences.profile_flags`

These nodes reference the files and documentation described below so the runtime always resolves provider metadata from audited sources.

## Provider protocol summary

`astroengine/providers/__init__.py` currently exposes a lightweight registry that keeps the runtime deterministic while longer-term provider plans incubate:

- **`EphemerisProvider` Protocol** — providers implement `positions_ecliptic(iso_utc, bodies)` to return longitude/declination maps for every requested body and `position(body, ts_utc)` to expose the canonical `BodyPosition` view. The protocol is intentionally narrow so detectors can rely on the same data shape whether the adapter is Swiss Ephemeris or Skyfield.
- **Registry helpers** — `register_provider(name, provider)`, `get_provider(name="swiss")`, and `list_providers()` maintain an in-memory catalogue populated during import time. `ensure_sweph_alias()` installs a compatibility shim so downstream code can import `swisseph` even when the host packages it as `pyswisseph`.
- **Autoregistration** — modules such as `astroengine.providers.skyfield_provider` and `astroengine.providers.swiss_provider` call `register_provider` when their dependencies load successfully. Implementations are encouraged to mirror this behaviour to keep the module → submodule → channel hierarchy intact.

## Bundled provider plans

Two provider designs ship in Markdown form to document expected behaviour:

- **Skyfield provider** (`astroengine/providers/skyfield_provider.md`): details cache warming for DE440s files, cadence policies (inners ≤6h, outers ≤24h, Moon 1h), light-time handling, and deterministic logging requirements. The notes also specify the metrics/events providers should emit.
- **Swiss Ephemeris provider** (`astroengine/providers/swe_provider.md`): outlines licensing considerations, dependency checks, delta-T configuration, and parity expectations relative to Skyfield.

The Swiss Ephemeris bridge (`astroengine/providers/swiss_provider.py`) ships today and the Skyfield provider registers itself when local JPL kernels are available. Design notes stay in Markdown form so future adapters (e.g., NASA Spice, HORIZONS) can align with the same provenance expectations before merging into the registry.

## Coordinate frames and cadences

Profiles reference providers through the following keys in `profiles/base_profile.yaml`:

- `providers.default` selects the primary plugin (`skyfield` by default).
- `providers.skyfield.cache_path` documents the expected ephemeris cache location (`${ASTROENGINE_CACHE}/skyfield/de440s`).
- `providers.swe.enabled` and `providers.swe.delta_t` illustrate how optional providers expose toggles.
- `providers.*.cadence_hours` define recommended sampling cadences by body class (`inner`, `outer`, `moon`, `minor`). Detectors should inherit these settings to keep the pipeline deterministic.
- Cadence and cache settings must be cross-checked against Solar Fire export intervals; record any deviations in the provenance log so comparisons remain valid.

House system and ayanamsha preferences are stored under `feature_flags.house_system` and `feature_flags.sidereal` in the same profile file. Detectors that rely on relocation/house calculations must combine those flags with provider metadata to select the correct frame.
Topocentric observer configuration (latitude, longitude, elevation) must be accepted without enabling atmospheric refraction; providers should default to geocentric calculations when no observer is supplied.

## Provenance & testing expectations

- Provider implementations should surface cache provenance through their backing adapters (e.g., SwissProvider relies on `astroengine.ephemeris.EphemerisAdapter` which records the ephemeris path and build). Expose the resolved `astroengine.canonical.BodyPosition` payloads without discarding provenance metadata returned by the adapter.
- Structured logging should include `provider_id`, call type (`query`, `query_window`, `prime_cache`), cache status, and timing information as described in the Skyfield design notes.
- Once implementations land, parity tests comparing providers (Skyfield vs. Swiss Ephemeris) should be added under `tests/` to guarantee positional differences stay within documented tolerances. Include Solar Fire export comparisons for representative charts and archive the export checksums.
- Environment validation via `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` should precede provider parity runs to confirm dependency versions.
- Record revisions to provider configurations and documentation according to `docs/governance/data_revision_policy.md` so provenance remains auditable.
- Providers must never fabricate values. When a dataset is unavailable (e.g., Solar Fire export missing), raise a provenance error rather than falling back to synthetic numbers.

Documenting the provider contract here ensures that future plugins remain compatible with the reworked environment while protecting the module hierarchy from accidental drift.
