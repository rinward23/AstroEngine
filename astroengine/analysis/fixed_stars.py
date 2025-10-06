"""Fixed star catalog utilities used by analysis endpoints."""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from importlib import resources

from ..astro.declination import OBLIQUITY_DEG
from ..core.stars_plus import Location, ParanPair, detect_parans
from ..core.stars_plus.catalog import Star as ParanStar

__all__ = [
    "Star",
    "StarDeclinationAspect",
    "load_catalog",
    "star_declination_aspects",
    "star_hits",
    "star_parans",
]


@dataclass(frozen=True, slots=True)
class Star:
    """Fixed star record sourced from packaged catalogs."""

    name: str
    lon_deg: float
    lat_deg: float
    mag: float
    ra_deg: float
    dec_deg: float

    @property
    def declination_deg(self) -> float:
        """Return the star declination in degrees."""

        return self.dec_deg


_CATALOG_FILES = {"robson": "fixed_stars.csv"}


def _ecliptic_to_equatorial(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Return (RA, Dec) in degrees for the supplied ecliptic position."""

    lon_rad = math.radians(lon_deg % 360.0)
    lat_rad = math.radians(lat_deg)
    eps_rad = math.radians(OBLIQUITY_DEG)

    sin_dec = math.sin(lat_rad) * math.cos(eps_rad) + math.cos(lat_rad) * math.sin(
        eps_rad
    ) * math.sin(lon_rad)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec = math.asin(sin_dec)

    y = math.sin(lon_rad) * math.cos(eps_rad) - math.tan(lat_rad) * math.sin(eps_rad)
    x = math.cos(lon_rad)
    ra = math.atan2(y, x)
    if ra < 0:
        ra += 2.0 * math.pi

    return math.degrees(ra), math.degrees(dec)


@cache
def _catalog_rows(catalog: str) -> tuple[Star, ...]:
    """Load and cache the fixed-star catalog defined by ``catalog``."""

    filename = _CATALOG_FILES.get(catalog.lower())
    if filename is None:
        raise ValueError(f"Unknown fixed star catalog: {catalog}")

    data_path = resources.files("astroengine.data").joinpath(filename)
    try:
        with resources.as_file(data_path) as path:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                stars = []
                for row in reader:
                    lon = float(row["lon_deg"])
                    lat = float(row["lat_deg"])
                    ra_deg, dec_deg = _ecliptic_to_equatorial(lon, lat)
                    stars.append(
                        Star(
                            name=row["name"].strip(),
                            lon_deg=lon,
                            lat_deg=lat,
                            mag=float(row["mag"]),
                            ra_deg=ra_deg,
                            dec_deg=dec_deg,
                        )
                    )
    except FileNotFoundError as exc:  # pragma: no cover - packaging error
        raise FileNotFoundError(f"Fixed star catalog missing: {data_path}") from exc

    if not stars:
        raise ValueError(f"Fixed star catalog '{catalog}' is empty")
    return tuple(stars)


def load_catalog(catalog: str = "robson") -> list[Star]:
    """Return the list of :class:`Star` entries for ``catalog``."""

    return list(_catalog_rows(catalog))


def _normalize_longitude(value: float) -> float:
    return value % 360.0


def _delta_longitude(star_lon: float, target_lon: float) -> float:
    """Return signed separation (degrees) from ``target_lon`` to ``star_lon``."""

    return ((star_lon - target_lon + 180.0) % 360.0) - 180.0


def star_hits(
    ecliptic_longitude: float,
    orbis: float,
    catalog: str = "robson",
) -> list[tuple[str, float]]:
    """Return fixed stars whose longitude lies within ``orbis`` degrees."""

    if orbis < 0:
        raise ValueError("Orb must be non-negative")

    target_lon = _normalize_longitude(ecliptic_longitude)
    hits: list[tuple[str, float]] = []
    for star in _catalog_rows(catalog):
        delta = _delta_longitude(star.lon_deg, target_lon)
        if abs(delta) <= orbis:
            hits.append((star.name, delta))
    hits.sort(key=lambda item: abs(item[1]))
    return hits


@dataclass(frozen=True, slots=True)
class StarDeclinationAspect:
    """Represents a declination parallel or contraparallel with a fixed star."""

    star: str
    target: str
    kind: str
    orb_deg: float
    declination_star: float
    declination_target: float
    magnitude: float


def star_declination_aspects(
    declinations: Mapping[str, float],
    orb_deg: float,
    catalog: str = "robson",
    *,
    include_parallel: bool = True,
    include_contraparallel: bool = True,
    magnitude_limit: float | None = None,
) -> list[StarDeclinationAspect]:
    """Return declination parallels/contraparallels between bodies and stars."""

    if orb_deg < 0:
        raise ValueError("Orb must be non-negative")
    if not declinations:
        return []
    if not include_parallel and not include_contraparallel:
        return []

    cleaned: dict[str, float] = {
        str(name): float(value) for name, value in declinations.items()
    }

    aspects: list[StarDeclinationAspect] = []
    for star in _catalog_rows(catalog):
        if magnitude_limit is not None and star.mag > magnitude_limit:
            continue
        for target, dec in cleaned.items():
            if include_parallel:
                diff = abs(star.dec_deg - dec)
                if diff <= orb_deg:
                    aspects.append(
                        StarDeclinationAspect(
                            star=star.name,
                            target=target,
                            kind="parallel",
                            orb_deg=diff,
                            declination_star=star.dec_deg,
                            declination_target=dec,
                            magnitude=star.mag,
                        )
                    )
            if include_contraparallel:
                diff = abs(star.dec_deg + dec)
                if diff <= orb_deg:
                    aspects.append(
                        StarDeclinationAspect(
                            star=star.name,
                            target=target,
                            kind="contraparallel",
                            orb_deg=diff,
                            declination_star=star.dec_deg,
                            declination_target=dec,
                            magnitude=star.mag,
                        )
                    )

    aspects.sort(key=lambda item: (item.orb_deg, item.star.lower(), item.target.lower()))
    return aspects


def star_parans(
    date_start: datetime,
    date_end: datetime,
    location: tuple[float, float],
    bodies: Sequence[str],
    provider_radec: Callable[[datetime, str], tuple[float, float]],
    catalog: str = "robson",
    *,
    event_pairs: Iterable[tuple[str, str]] | None = None,
    magnitude_limit: float | None = None,
    tolerance_minutes: float = 8.0,
    step_days: int = 1,
) -> list[dict[str, object]]:
    """Return paran events for the supplied ``bodies`` and ``location``.

    Parameters
    ----------
    date_start, date_end:
        UTC datetimes delimiting the inclusive scan range.
    location:
        ``(lat_deg, lon_east_deg)`` tuple.
    bodies:
        Names of moving bodies (e.g., planets) for which RA/Dec will be provided.
    provider_radec:
        Callable returning ``(ra_deg, dec_deg)`` for the body at a given datetime.
    event_pairs:
        Sequence of ``(star_event, planet_event)`` strings; defaults to the
        common paran combinations if omitted.
    magnitude_limit:
        Skip stars with visual magnitude greater than this value.
    tolerance_minutes:
        Maximum allowed separation between the star and planet event times.
    step_days:
        Day increment when scanning the ``[date_start, date_end]`` window.
    """

    if date_end < date_start:
        raise ValueError("date_end must not precede date_start")
    if not bodies:
        return []

    lat_deg, lon_deg = float(location[0]), float(location[1])

    if event_pairs is None:
        event_pairs = (
            ("culminate", "rise"),
            ("culminate", "set"),
            ("rise", "culminate"),
            ("set", "culminate"),
        )

    allowed_events = {"rise", "set", "culminate"}
    for star_event, planet_event in event_pairs:
        if star_event not in allowed_events or planet_event not in allowed_events:
            raise ValueError("Unsupported event in event_pairs")

    star_catalog: dict[str, ParanStar] = {}
    for star in _catalog_rows(catalog):
        if magnitude_limit is not None and star.mag > magnitude_limit:
            continue
        star_catalog[star.name] = ParanStar(
            name=star.name,
            ra_deg=star.ra_deg,
            dec_deg=star.dec_deg,
            vmag=star.mag,
        )

    if not star_catalog:
        return []

    pairs = [
        ParanPair(
            star_name=star_name,
            planet_name=body,
            star_event=star_event,
            planet_event=planet_event,
        )
        for star_name in star_catalog
        for body in bodies
        for star_event, planet_event in event_pairs
    ]

    events = detect_parans(
        date_start=date_start,
        date_end=date_end,
        location=Location(lat_deg=lat_deg, lon_east_deg=lon_deg),
        stars=star_catalog,
        provider_radec=provider_radec,
        pairs=pairs,
        tol_minutes=float(tolerance_minutes),
        step_days=int(step_days),
    )

    results: list[dict[str, object]] = []
    for event in events:
        payload = {"kind": event.kind, "time": event.time}
        payload.update(event.meta)
        results.append(payload)
    return results
