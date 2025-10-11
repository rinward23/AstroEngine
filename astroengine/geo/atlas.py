"""Atlas geocoding helpers with offline and online fallbacks."""

from __future__ import annotations

import importlib
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from astroengine.atlas.geocoder import (
    AddressComponents,
    AddressParser,
    load_builtin_parser,
    normalize_token,
)
from astroengine.atlas.tz import tzid_for
from astroengine.config import Settings
from astroengine.runtime_config import runtime_settings
from astroengine.infrastructure.storage.sqlite import apply_default_pragmas


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


@lru_cache(maxsize=1)
def _address_parser() -> AddressParser:
    return load_builtin_parser()


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

    parser = _address_parser()
    components = parser.parse(trimmed)
    normalized_query = components.normalised_query() or trimmed

    cfg = _extract_config(settings or runtime_settings.persisted())
    offline_failure: Exception | None = None

    if cfg.offline_enabled and cfg.data_path is not None:
        try:
            return _geocode_offline(normalized_query, cfg.data_path, components)
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
        return _geocode_online(normalized_query, components)
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


def _geocode_offline(
    query: str,
    db_path: Path,
    components: AddressComponents | None = None,
) -> GeocodeResult:
    if not db_path.exists():
        raise AtlasLookupError(f"Offline atlas database not found at {db_path}.")

    normalized_variants: list[str] = []
    if components is not None:
        comp_query = normalize_token(components.normalised_query())
        if comp_query:
            normalized_variants.append(comp_query)
        base = components.as_dict()
        city_country = " ".join(
            value
            for value in (base.get("city"), base.get("admin1"), base.get("country"))
            if value
        )
        candidate = normalize_token(city_country)
        if candidate:
            normalized_variants.append(candidate)
    normalized_variants.append(_normalize(query))
    deduped: list[str] = []
    for item in normalized_variants:
        if item and item not in deduped:
            deduped.append(item)

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        apply_default_pragmas(conn)
        row = None
        for normalized in deduped:
            row = conn.execute(
                """
                SELECT name, latitude, longitude, tzid
                FROM places
                WHERE search_name = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            if row:
                break
        if row is None:
            for normalized in deduped:
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
                if row:
                    break

    if row is None:
        raise AtlasLookupError(f"No offline atlas entry matched '{query}'.")

    tzid = row["tzid"] or tzid_for(float(row["latitude"]), float(row["longitude"]))
    return {
        "name": row["name"],
        "lat": float(row["latitude"]),
        "lon": float(row["longitude"]),
        "tz": tzid,
    }


def _geocode_online(query: str, components: AddressComponents | None = None) -> GeocodeResult:
    if importlib.util.find_spec("geopy.geocoders") is None:  # pragma: no cover - optional dep guard
        raise AtlasLookupError(
            "Online geocoding requires the 'geopy' extra or enable the offline atlas dataset."
        )

    geocoders = importlib.import_module("geopy.geocoders")
    Nominatim = geocoders.Nominatim
    geocoder = Nominatim(user_agent="astroengine")
    search_query = components.normalised_query() if components else query
    location = geocoder.geocode(search_query or query, exactly_one=True, timeout=10)
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
    return normalize_token(text)

