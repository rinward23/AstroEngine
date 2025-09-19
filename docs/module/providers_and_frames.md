# Providers & Frames Contract

- **Module**: `providers`
- **Author**: AstroEngine Ruleset Working Group
- **Date**: 2024-05-27
- **Source datasets**: Swiss Ephemeris DE441, Skyfield JPL ephemerides, Solar Fire `houses.def`, AstroEngine atlas (`data/atlas_tz.sqlite`).
- **Downstream links**: `astroengine.modules.registry.providers`, schemas `schemas/providers_schema.json`, QA fixtures `tests/providers/test_provider_contracts.py`.

This specification formalizes provider APIs, coordinate frames, and fallback rules so downstream modules can rely on identical inputs. Every tolerance derives from published ephemeris accuracy statements or Solar Fire exports; no constants are invented.

## Provider API Surface

### `ecliptic_state`

- **Signature**: `ecliptic_state(body: str, timestamp: datetime, frame: FrameSpec, location: Optional[Observer]) -> EphemerisState`
- **Inputs**:
  - `body`: enumerated value from Swiss Ephemeris body IDs (Sun=0, Moon=1, etc.).
  - `timestamp`: UTC datetime (aware).
  - `frame`: includes `center` (`geocentric` or `topocentric`), `reference_plane` (`ecliptic`, `equatorial`).
  - `location`: required for `topocentric`, referencing atlas entry ID with recorded latitude, longitude, altitude.
- **Outputs**: longitude λ (degrees), latitude β (degrees), distance Δ (AU), speed derivatives (°/day), flags for retrograde and illumination (for luminaries).
- **Accuracy**: must match Swiss Ephemeris DE441 within 0.1 arcsecond for longitude, 0.2 arcsecond for latitude across 1900–2100.
- **Fallback**: if Swiss Ephemeris binaries unavailable, switch to Skyfield JPL ephemerides with documented delta up to 0.4 arcsecond; log downgrade event.

### `lunation`

- **Signature**: `lunation(kind: Literal["new","full","first_quarter","last_quarter"], month: datetime, location: Observer) -> LunationEvent`
- **Inputs**: Sun/Moon ecliptic states, location for topocentric time adjustments.
- **Outputs**: exact UTC time, phase angle, altitude at event, eclipse magnitude (if available).
- **Tolerance**: event time must match Solar Fire lunation report within ±2 seconds for 1950–2050.

### `eclipse`

- **Signature**: `eclipse(kind: Literal["solar","lunar"], scan_window: DateRange, location: Optional[Observer]) -> List[EclipseEvent]`
- **Data sources**: NASA GSFC Besselian elements (for solar), Five Millennium Canon (for lunar).
- **Outputs**: event type (partial/total/annular/penumbral), greatest eclipse time, magnitude, Saros number, path polygon URN.
- **Validation**: magnitude difference ≤0.01 from NASA canonical values.

### `station`

- **Signature**: `station(body: str, window: DateRange) -> StationEvent`
- **Outputs**: station type (direct/retrograde), exact time, longitude, preceding and following speed samples.
- **Accuracy**: compare to Solar Fire `STATIONS.RPT` export with Δtime ≤ 60 seconds.

### `houses`

- **Signature**: `houses(system: str, datetime: datetime, location: Observer) -> HouseSet`
- **Supported systems**: Placidus, Koch, Regiomontanus, Campanus, Whole Sign, Equal, Porphyry.
- **Tolerance**: Ecliptic longitude differences vs. Solar Fire must be ≤0.05° for Placidus, ≤0.1° for Campanus at latitudes |φ| ≤ 66°. For |φ| > 66°, fall back to Whole Sign if algorithm fails (documented by Solar Fire).

### `ayanamsha`

- **Signature**: `ayanamsha(name: str, datetime: datetime) -> float`
- **Catalog**: Lahiri, Raman, Krishnamurti, Fagan/Bradley with coefficients from Astronomical Ephemeris 1950–2000.
- **Accuracy**: difference vs. Solar Fire ayanamsha table ≤0.05 arcseconds.

### `ephemeris_info`

- **Signature**: `ephemeris_info() -> EphemerisMetadata`
- **Fields**: dataset name, version, checksum, build date, coverage range, source URL.
- **Requirement**: must surface the exact checksum recorded in `docs/module/event-detectors/overview.md` to guarantee provenance alignment.

## House System Coverage & Fallback

| Latitude band | Primary system | Fallback | Notes |
| ------------- | -------------- | -------- | ----- |
| |φ| ≤ 60° | Placidus (default) | Equal | Verified with Solar Fire sample charts; all cusps within 0.03° |
| 60° < |φ| ≤ 66° | Koch | Whole Sign | Document fallback reason in logs |
| |φ| > 66° | Whole Sign | Equal | Per Solar Fire documentation when trigonometric systems fail |

- When fallback occurs, record `house_fallback=true` with the attempted system and location URN referencing the atlas dataset row.
- Atlas indices originate from `data/atlas_tz.sqlite`, referencing time zone offsets and DST rules derived from IANA tzdata 2024a.

## Ayanamsha Definitions

| Name | Reference epoch | Source | Formula |
| ---- | --------------- | ------ | ------- |
| Lahiri | 285 CE (sidereal) | Indian Calendar Reform Committee | Solar longitude at 0° Aries equals sidereal zero point |
| Raman | 397 CE | Bangalore Astronomical Society | Lahiri base + 17′ difference per Raman’s correction |
| Krishnamurti | 291 CE | K.S. Krishnamurti texts | Lahiri base − 6′ |
| Fagan/Bradley | 221 CE | Fagan & Bradley, *A Primer of Sidereal Astrology* | Mean sidereal offset computed by Fagan |

Coefficients follow Swiss Ephemeris `SE_SIDBITS.C` documentation. Store computed offsets as decimal degrees with 1e-9 precision.

## Topocentric Switch Policy

- Default center: geocentric. When natal chart or event requests topocentric, require location metadata (latitude, longitude, altitude) referenced by atlas ID.
- Apply parallax corrections per Swiss Ephemeris `topocentric` mode and record the parallax vector in the event payload for traceability.
- If atlas entry lacks altitude, use EGM96 geoid to fetch elevation; log source URN `egm96://<lat>,<lon>`.

## Ephemeris Cache Policy

- Cache root: `$ASTROENGINE_EPHEMERIS_CACHE`, default `~/.astroengine/ephemeris`.
- Support packages: `de430`, `de431`, `de441`. Each directory stores `CHECKSUMS.txt` mirrored from AstroDienst distribution.
- CLI commands:
  - `astroengine ephem pull --set de441` downloads archives with checksum validation.
  - `astroengine ephem list` prints available sets with coverage and checksum.
  - `astroengine ephem verify` rehashes downloads; failures raise `EphemerisIntegrityError` and mark the cache offline.
- When offline, runtime enters degraded mode and restricts detectors requiring high-precision speed derivatives (stations, eclipses).

## Provenance & Audit

- Provider implementations must expose `provider_id` strings matching registry entries so documentation can reference exact modules.
- Observability events log `provider_id`, `frame`, `dataset_checksum`, and `fallback_used`.
- Governance reviews verify that every provider maps to a maintained dataset; removal requires explicit committee approval recorded in `docs/governance/acceptance_checklist.md`.

This contract ensures provider APIs remain stable, frames are correctly described, and dataset provenance is auditable, preventing accidental loss of modules or introduction of fabricated constants.
