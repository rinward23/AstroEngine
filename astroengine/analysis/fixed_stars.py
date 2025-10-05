"""Fixed star catalog utilities used by analysis endpoints."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

__all__ = ["Star", "load_catalog", "star_hits"]


@dataclass(frozen=True, slots=True)
class Star:
    """Minimal fixed star record sourced from packaged catalogs."""

    name: str
    lon_deg: float
    lat_deg: float
    mag: float


_CATALOG_FILES = {"robson": "fixed_stars.csv"}


@lru_cache(maxsize=None)
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
                stars = [
                    Star(
                        name=row["name"].strip(),
                        lon_deg=float(row["lon_deg"]),
                        lat_deg=float(row["lat_deg"]),
                        mag=float(row["mag"]),
                    )
                    for row in reader
                ]
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
