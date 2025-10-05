"""Atlas geocoding helpers with offline and online fallbacks."""

from __future__ import annotations

import importlib
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from astroengine.atlas.tz import tzid_for
from astroengine.config import Settings, load_settings


class GeocodeResult(TypedDict):
    """Normalized geocode payload returned by :func:`geocode`."""

    name: str
    lat: float
    lon: float
    tz: str


class AtlasLookupError(RuntimeError):
    """Raised when a geocode operation cannot be satisfied."""


@dataclass(slots=True)
class _AtlasConfig:
    offline_enabled: bool
    data_path: Path | None
    online_fallback_enabled: bool


def geocode(query: str, *, settings: Settings | None = None) -> GeocodeResult:
    """Resolve ``query`` into coordinates and timezone information.

    Parameters
    ----------
    query:
        Free-form place name to resolve.
    settings:
        Optional settings override used primarily for testing. When omitted the
        persisted :func:`astroengine.config.load_settings` result is used.

    Returns
    -------
    GeocodeResult
        Mapping containing the resolved place name, latitude, longitude and
        timezone identifier.

    Raises
    ------
    AtlasLookupError
        If both offline and online providers fail to satisfy the lookup.
    ValueError
        If ``query`` is empty or blank.
    """

    trimmed = query.strip()
    if not trimmed:
        raise ValueError("Geocode query must not be empty.")

    cfg = _extract_config(settings or load_settings())
    offline_failure: Exception | None = None

    if cfg.offline_enabled and cfg.data_path is not None:
        try:
            return _geocode_offline(trimmed, cfg.data_path)
        except AtlasLookupError as exc:
            offline_failure = exc

    if not cfg.online_fallback_enabled:
        if offline_failure:
            raise AtlasLookupError(
                f"Offline atlas lookup failed ({offline_failure}). Online fallback is disabled in settings."
            ) from offline_failure
        raise AtlasLookupError(
            "Online atlas fallback is disabled. Enable the offline atlas dataset or allow the online fallback in settings."
        )

    try:
        return _geocode_online(trimmed)
    except AtlasLookupError as online_exc:
        if offline_failure:
            raise AtlasLookupError(
                f"Offline atlas lookup failed ({offline_failure}). Online provider unavailable: {online_exc}"
            ) from online_exc
        raise online_exc


def _extract_config(settings: Settings) -> _AtlasConfig:
    atlas_cfg = getattr(settings, "atlas", None)
    if atlas_cfg is None:
        return _AtlasConfig(False, None, False)
    data_path = Path(atlas_cfg.data_path).expanduser() if atlas_cfg.data_path else None
    return _AtlasConfig(
        bool(atlas_cfg.offline_enabled),
        data_path,
        bool(getattr(atlas_cfg, "online_fallback_enabled", False)),
    )


def _geocode_offline(query: str, db_path: Path) -> GeocodeResult:
    if not db_path.exists():
        raise AtlasLookupError(f"Offline atlas database not found at {db_path}.")

    normalized = _normalize(query)
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT name, latitude, longitude, tzid
            FROM places
            WHERE search_name = ?
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT name, latitude, longitude, tzid
                FROM places
                WHERE search_name LIKE ?
                ORDER BY population DESC
                LIMIT 1
                """,
                (f"%{normalized}%",),
            ).fetchone()

    if row is None:
        raise AtlasLookupError(f"No offline atlas entry matched '{query}'.")

    tzid = row["tzid"] or tzid_for(float(row["latitude"]), float(row["longitude"]))
    return {
        "name": row["name"],
        "lat": float(row["latitude"]),
        "lon": float(row["longitude"]),
        "tz": tzid,
    }


def _geocode_online(query: str) -> GeocodeResult:
    if importlib.util.find_spec("geopy.geocoders") is None:  # pragma: no cover - optional dep guard
        raise AtlasLookupError(
            "Online geocoding requires the 'geopy' extra or enable the offline atlas dataset."
        )

    geocoders = importlib.import_module("geopy.geocoders")
    Nominatim = getattr(geocoders, "Nominatim")
    geocoder = Nominatim(user_agent="astroengine")
    location = geocoder.geocode(query, exactly_one=True, timeout=10)
    if location is None:
        raise AtlasLookupError(f"No online geocode result matched '{query}'.")

    tzid = tzid_for(float(location.latitude), float(location.longitude))
    return {
        "name": getattr(location, "address", query),
        "lat": float(location.latitude),
        "lon": float(location.longitude),
        "tz": tzid,
    }


def _normalize(text: str) -> str:
    cleaned = unicodedata.normalize("NFKD", text)
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch.isspace())
    return " ".join(cleaned.lower().split())

