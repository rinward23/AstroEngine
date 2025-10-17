# >>> AUTO-GEN BEGIN: positions-cache v1.0
from __future__ import annotations

import atexit
import logging
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from time import perf_counter

from ..canonical import canonical_round, normalize_longitude, normalize_speed_per_day
from ..core.time import julian_day
from ..ephemeris import SwissEphemerisAdapter
from ..ephemeris.swe import swe
from ..infrastructure.home import ae_home
from ..infrastructure.storage.sqlite import apply_default_pragmas

CACHE_DIR = ae_home() / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB = CACHE_DIR / "positions.sqlite"

_LOGGER = logging.getLogger(__name__)

_CONNECTION: sqlite3.Connection | None = None
_INITIALIZED = False

_BODY_CODES = {
    "sun": "SUN",
    "moon": "MOON",
    "mercury": "MERCURY",
    "venus": "VENUS",
    "mars": "MARS",
    "jupiter": "JUPITER",
    "saturn": "SATURN",
    "uranus": "URANUS",
    "neptune": "NEPTUNE",
    "pluto": "PLUTO",
}

_SUPPORTED_BODIES = set(_BODY_CODES)

_SQL = {
    "init": """
CREATE TABLE IF NOT EXISTS positions_daily (
  day_jd INTEGER NOT NULL,
  body TEXT NOT NULL,
  lon REAL NOT NULL,
  lat REAL,
  speed REAL,
  PRIMARY KEY (day_jd, body)
);
CREATE INDEX IF NOT EXISTS ix_positions_daily_day_body
  ON positions_daily(day_jd, body);
""",
    "get": "SELECT lon FROM positions_daily WHERE day_jd=? AND body=?",
    "get_full": "SELECT lon, lat, speed FROM positions_daily WHERE day_jd=? AND body=?",
    "upsert": (
        "INSERT OR REPLACE INTO positions_daily(day_jd, body, lon, lat, speed)"
        " VALUES (?,?,?,?,?)"
    ),
}


def _close_connection() -> None:
    global _CONNECTION, _INITIALIZED

    if _CONNECTION is not None:
        try:
            _CONNECTION.close()
        finally:  # pragma: no cover - defensive guard
            _CONNECTION = None
            _INITIALIZED = False


def _get_connection() -> sqlite3.Connection:
    global _CONNECTION, _INITIALIZED

    if _CONNECTION is None:
        con = sqlite3.connect(str(DB))
        apply_default_pragmas(con)
        _CONNECTION = con
        atexit.register(_close_connection)

    assert _CONNECTION is not None  # narrow type for mypy

    if not _INITIALIZED:
        _CONNECTION.executescript(_SQL["init"])
        _CONNECTION.commit()
        _INITIALIZED = True

    return _CONNECTION


def _day_jd(jd_ut: float) -> int:
    return int(jd_ut)


def _ensure_swiss_available() -> bool:
    from ..detectors import common as detectors_common  # late import to avoid cycles

    return detectors_common._ensure_swiss()


def supported_body(body: str) -> bool:
    return body.lower() in _SUPPORTED_BODIES


def get_daily_entry(
    jd_ut: float, body: str
) -> tuple[float, float | None, float | None]:
    normalized = body.lower()
    con = _get_connection()
    cur = con.cursor()
    try:
        cur.execute(_SQL["get_full"], (_day_jd(jd_ut), normalized))
        row = cur.fetchone()
    finally:
        cur.close()
    if row is not None:
        lon, lat, speed = row
        lon_f = normalize_longitude(float(lon))
        lat_f = None if lat is None else canonical_round(float(lat))
        speed_f = (
            None if speed is None else normalize_speed_per_day(float(speed))
        )
        return lon_f, lat_f, speed_f

    if not _ensure_swiss_available():
        raise RuntimeError("Swiss ephemeris unavailable for cache compute")
    try:
        code = int(getattr(swe, _BODY_CODES[normalized]))
    except (KeyError, AttributeError) as exc:
        raise ValueError(f"Unsupported body '{body}' for daily cache") from exc
    adapter = SwissEphemerisAdapter.get_default_adapter()
    sample = adapter.body_position(float(_day_jd(jd_ut)), code, body_name=body.title())
    lon = normalize_longitude(float(sample.longitude))
    lat = canonical_round(float(sample.latitude))
    speed = normalize_speed_per_day(float(sample.speed_longitude))
    con = _get_connection()
    cur = con.cursor()
    try:
        cur.execute(
            _SQL["upsert"],
            (
                _day_jd(jd_ut),
                normalized,
                lon,
                lat,
                speed,
            ),
        )
    finally:
        cur.close()
    con.commit()
    return lon, lat, speed


def get_lon_daily(jd_ut: float, body: str) -> float:
    lon, _, _ = get_daily_entry(jd_ut, body)
    return float(lon)


def warm_daily(bodies: Iterable[str], start_jd: float, end_jd: float) -> int:
    count = 0
    jd = int(start_jd)
    end = int(end_jd)
    if end < jd:
        return 0

    cached_bodies = tuple(body.lower() for body in bodies)
    for day in range(jd, end + 1):
        day_jd = float(day)
        for body in cached_bodies:
            get_daily_entry(day_jd, body)
            count += 1
    return count


_BOOTSTRAP_BODIES: tuple[str, ...] = ("sun", "moon", "mercury")
_BOOTSTRAP_DAY_OFFSETS: tuple[int, ...] = (0, 1)


def warm_startup_grid(
    *,
    max_duration_ms: float = 150.0,
    bodies: Sequence[str] | None = None,
    day_offsets: Sequence[int] | None = None,
) -> int:
    """Warm a small JD/body grid for cold starts within ``max_duration_ms``.

    The helper focuses on the most frequently accessed luminaries so
    subsequent requests can rely on cached Swiss Ephemeris results.  The
    warm-up stops immediately when ``max_duration_ms`` is exceeded to
    ensure startup remains bounded.
    """

    if max_duration_ms <= 0:
        return 0

    selected_bodies = tuple(
        body.lower()
        for body in (bodies or _BOOTSTRAP_BODIES)
        if supported_body(body)
    )
    if not selected_bodies:
        return 0

    offsets = tuple(int(offset) for offset in (day_offsets or _BOOTSTRAP_DAY_OFFSETS))
    if not offsets:
        return 0

    start = perf_counter()
    warmed = 0

    base_day = int(julian_day(datetime.now(tz=UTC)))

    for offset in offsets:
        for body in selected_bodies:
            elapsed_ms = (perf_counter() - start) * 1000.0
            if elapsed_ms >= max_duration_ms:
                return warmed
            day_jd = float(base_day + offset)
            try:
                get_daily_entry(day_jd, body)
            except RuntimeError:
                _LOGGER.debug("Startup warm skipped; Swiss ephemeris unavailable.")
                return warmed
            except Exception as exc:  # pragma: no cover - defensive guard
                _LOGGER.warning(
                    "Startup warm failed for %s @ JD %s: %s", body, day_jd, exc
                )
                return warmed
            warmed += 1
    return warmed


# >>> AUTO-GEN END: positions-cache v1.0
