"""Batch return scanning orchestration."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ...core.bodies import canonical_name
from ...core.charts_plus.returns import ReturnWindow as LegacyReturnWindow
from ...core.charts_plus.returns import find_returns_in_window as legacy_find_returns
from ...core.time import ensure_utc, to_tt
from ...ephemeris import EphemerisAdapter
from ...scoring.policy import OrbPolicy, load_orb_policy
from ..angles.houses import GeoLoc, HousesResult, compute_angles_houses
from ._codes import resolve_body_code
from .attach import attach_aspects_to_natal, attach_transiting_aspects
from .finder import ReturnInstant, ReturnNotFoundError, find_return_instant

__all__ = [
    "AttachOptions",
    "GeoLoc",
    "NatalCtx",
    "PositionSnapshot",
    "ReturnHit",
    "ScanOptions",
    "scan_returns",
]


@dataclass(frozen=True)
class PositionSnapshot:
    """Captured ephemeris sample for a body at the return instant."""

    longitude: float
    latitude: float
    distance_au: float
    speed_longitude: float
    speed_latitude: float
    speed_distance: float
    right_ascension: float
    declination: float
    speed_ra: float
    speed_declination: float

    def to_mapping(self) -> dict[str, float]:
        return {
            "lon": self.longitude,
            "lat": self.latitude,
            "distance": self.distance_au,
            "speed_lon": self.speed_longitude,
            "speed_lat": self.speed_latitude,
            "speed_dist": self.speed_distance,
            "ra": self.right_ascension,
            "decl": self.declination,
            "speed_ra": self.speed_ra,
            "speed_decl": self.speed_declination,
        }


@dataclass(frozen=True)
class NatalCtx:
    """Natal context supplying longitudes and reference metadata."""

    moment: datetime
    longitudes: Mapping[str, float]
    location: GeoLoc | None = None
    zodiac: str = "tropical"
    ayanamsha: str | None = None


@dataclass(frozen=True)
class AttachOptions:
    """Toggle which attachments should be computed during scans."""

    transiting_aspects: bool = True
    to_natal: bool = False


@dataclass(frozen=True)
class ScanOptions:
    """User-specified configuration for scanning return windows."""

    location: GeoLoc | None = None
    house_system: str = "placidus"
    harmonics: Sequence[int] = field(default_factory=lambda: (1, 2, 3, 4, 5, 6))
    orb_policy: OrbPolicy = field(default_factory=load_orb_policy)
    attach: AttachOptions = field(default_factory=AttachOptions)
    tz_hint: str | None = None


@dataclass(frozen=True)
class ReturnHit:
    """Aggregated return information exposed to API/UI layers."""

    body: str
    instant: ReturnInstant
    location: GeoLoc
    houses: HousesResult
    positions: Mapping[str, PositionSnapshot]
    transiting_aspects: Sequence
    natal_aspects: Sequence
    metadata: Mapping[str, object]

    def as_dict(self) -> dict[str, object]:
        payload = {
            "body": self.body,
            "instant": self.instant.as_dict(),
            "location": {
                "latitude": self.location.latitude_deg,
                "longitude": self.location.longitude_deg,
                "elevation": self.location.elevation_m,
            },
            "houses": self.houses.to_mapping(),
            "positions": {name: snap.to_mapping() for name, snap in self.positions.items()},
            "transiting_aspects": [hit.__dict__ for hit in self.transiting_aspects],
            "natal_aspects": [hit.__dict__ for hit in self.natal_aspects],
            "metadata": dict(self.metadata),
        }
        return payload


def _ensure_location(options: ScanOptions, natal: NatalCtx) -> GeoLoc:
    if options.location is not None:
        return options.location
    if natal.location is not None:
        return natal.location
    raise ValueError("Return scans require a location to compute houses.")


def _positions_payload(
    instant: ReturnInstant,
    adapter: EphemerisAdapter,
    bodies: Iterable[str],
) -> dict[str, object]:
    payload: dict[str, object] = {"timestamp": instant.exact_time.isoformat().replace("+00:00", "Z"), "bodies": {}}
    conversion = to_tt(instant.exact_time.astimezone(UTC))
    for body in bodies:
        code = resolve_body_code(body).code
        sample = adapter.sample(code, conversion)
        payload["bodies"][body] = {
            "lon": sample.longitude % 360.0,
            "lat": sample.latitude,
            "distance": sample.distance,
            "speed_lon": sample.speed_longitude,
            "speed_lat": sample.speed_latitude,
            "speed_dist": sample.speed_distance,
            "ra": sample.right_ascension,
            "decl": sample.declination,
            "speed_ra": sample.speed_right_ascension,
            "speed_decl": sample.speed_declination,
        }
    return payload


def _positions_snapshots(
    instant: ReturnInstant,
    adapter: EphemerisAdapter,
    bodies: Iterable[str],
) -> dict[str, PositionSnapshot]:
    conversion = to_tt(instant.exact_time.astimezone(UTC))
    snapshots: dict[str, PositionSnapshot] = {}
    for body in bodies:
        code = resolve_body_code(body).code
        sample = adapter.sample(code, conversion)
        snapshots[body] = PositionSnapshot(
            longitude=sample.longitude % 360.0,
            latitude=sample.latitude,
            distance_au=sample.distance,
            speed_longitude=sample.speed_longitude,
            speed_latitude=sample.speed_latitude,
            speed_distance=sample.speed_distance,
            right_ascension=sample.right_ascension,
            declination=sample.declination,
            speed_ra=sample.speed_right_ascension,
            speed_declination=sample.speed_declination,
        )
    return snapshots


def _metadata_for(adapter: EphemerisAdapter, instant: ReturnInstant) -> dict[str, object]:
    config = getattr(adapter, "_config", None)
    zodiac = "sidereal" if getattr(config, "sidereal", False) else "tropical"
    ayanamsha = getattr(config, "sidereal_mode", None)
    return {
        "zodiac": zodiac,
        "ayanamsha": ayanamsha,
        "delta_t_seconds": instant.delta_t_seconds,
        "tolerance_seconds": instant.tolerance_seconds,
    }


def _synodic_period_days(body: str) -> float:
    from .finder import _MEAN_PERIODS_DAYS  # type: ignore[attr-defined]

    return _MEAN_PERIODS_DAYS.get(body.lower(), 365.2422)


def scan_returns(
    ephem: EphemerisAdapter,
    bodies: Sequence[str],
    t_from: datetime,
    t_to: datetime,
    natal: NatalCtx,
    options: ScanOptions | None = None,
) -> list[ReturnHit]:
    """Scan the supplied window for return hits across ``bodies``."""

    if not bodies:
        return []
    options = options or ScanOptions()
    location = _ensure_location(options, natal)
    start = ensure_utc(t_from)
    end = ensure_utc(t_to)
    if end <= start:
        raise ValueError("t_to must be after t_from")

    hits: list[ReturnHit] = []
    harmonics = options.harmonics

    for body in bodies:
        target_key = canonical_name(body)
        try:
            target_lon = natal.longitudes[target_key]
        except KeyError as exc:
            raise KeyError(f"Natal longitude for {body} missing from context") from exc

        last_emitted: datetime | None = None
        period_days = _synodic_period_days(body)
        margin = timedelta(days=period_days)

        code = resolve_body_code(body).code

        def _provider(moment: datetime) -> dict[str, float]:
            conversion = to_tt(moment)
            sample = ephem.sample(code, conversion)
            return {body: sample.longitude % 360.0}

        legacy_window = LegacyReturnWindow(
            start=start - margin,
            end=end + margin,
        )

        step_minutes = max(15, int(period_days * 24.0 * 60.0 / 96.0))

        coarse_results = legacy_find_returns(
            body,
            target_lon,
            legacy_window,
            _provider,
            step_minutes=step_minutes,
            tol_seconds=1.0,
        )

        for coarse in coarse_results:
            approx = ensure_utc(coarse.exact_time)
            refine_window = (
                approx - timedelta(days=period_days * 0.25),
                approx + timedelta(days=period_days * 0.25),
            )
            try:
                instant = find_return_instant(
                    ephem,
                    body,
                    target_lon,
                    refine_window,
                    tz_hint=options.tz_hint,
                )
            except ReturnNotFoundError:
                continue

            if instant.exact_time < start or instant.exact_time > end:
                continue

            if instant.delta_arcsec > 5.0:
                continue

            if last_emitted is not None:
                min_spacing = max(1.0, period_days * 0.1) * 86400.0
                if abs((instant.exact_time - last_emitted).total_seconds()) < min_spacing:
                    continue

            houses = compute_angles_houses(
                instant.exact_time,
                location,
                system=options.house_system,
            )
            tracked_bodies = tuple(dict.fromkeys([body, *bodies]))
            snapshots = _positions_snapshots(instant, ephem, tracked_bodies)
            position_payload = _positions_payload(instant, ephem, tracked_bodies)
            transiting_aspects = (
                attach_transiting_aspects(position_payload, options.orb_policy, harmonics)
                if options.attach.transiting_aspects
                else []
            )
            natal_aspects = (
                attach_aspects_to_natal(position_payload, natal.longitudes, options.orb_policy, harmonics)
                if options.attach.to_natal
                else []
            )

            hit = ReturnHit(
                body=body,
                instant=instant,
                location=location,
                houses=houses,
                positions=snapshots,
                transiting_aspects=transiting_aspects,
                natal_aspects=natal_aspects,
                metadata=_metadata_for(ephem, instant),
            )
            hits.append(hit)
            last_emitted = instant.exact_time

    hits.sort(key=lambda item: item.instant.exact_time)
    return hits
