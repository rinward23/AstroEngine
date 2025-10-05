# >>> AUTO-GEN BEGIN: positions-cache v1.0
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
import numpy as np

from ..canonical import canonical_round, normalize_longitude, normalize_speed_per_day
from ..ephemeris import SwissEphemerisAdapter
from ..infrastructure.home import ae_home

CACHE_DIR = ae_home() / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB = CACHE_DIR / "positions.sqlite"

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


def _connect():
    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.executescript(_SQL["init"])
    con.commit()
    return con


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
    con = _connect()
    try:
        cur = con.execute(_SQL["get_full"], (_day_jd(jd_ut), normalized))
        row = cur.fetchone()
        if row is not None:
            lon, lat, speed = row
            lon_f = normalize_longitude(float(lon))
            lat_f = None if lat is None else canonical_round(float(lat))
            speed_f = (
                None
                if speed is None
                else normalize_speed_per_day(float(speed))
            )
            return lon_f, lat_f, speed_f
    finally:
        con.close()

    if not _ensure_swiss_available():
        raise RuntimeError("Swiss ephemeris unavailable for cache compute")
    import swisseph as swe  # type: ignore

    try:
        code = int(getattr(swe, _BODY_CODES[normalized]))
    except (KeyError, AttributeError) as exc:
        raise ValueError(f"Unsupported body '{body}' for daily cache") from exc
    adapter = SwissEphemerisAdapter.get_default_adapter()
    sample = adapter.body_position(float(_day_jd(jd_ut)), code, body_name=body.title())
    lon = normalize_longitude(float(sample.longitude))
    lat = canonical_round(float(sample.latitude))
    speed = normalize_speed_per_day(float(sample.speed_longitude))
    con = _connect()
    try:
        con.execute(
            _SQL["upsert"],
            (
                _day_jd(jd_ut),
                normalized,
                lon,
                lat,
                speed,
            ),
        )
        con.commit()
    finally:
        con.close()
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

    days = np.arange(jd, end + 1, dtype=np.int64)
    cached_bodies = tuple(body.lower() for body in bodies)
    for day in days:
        day_jd = float(day)
        for body in cached_bodies:
            get_daily_entry(day_jd, body)
            count += 1
    return count


# >>> AUTO-GEN END: positions-cache v1.0
