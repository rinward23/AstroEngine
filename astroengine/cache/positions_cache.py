# >>> AUTO-GEN BEGIN: positions-cache v1.0
from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from ..ephemeris import SwissEphemerisAdapter
from ..infrastructure.home import ae_home

CACHE_DIR = ae_home() / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB = CACHE_DIR / "positions.sqlite"

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
""",
    "get": "SELECT lon FROM positions_daily WHERE day_jd=? AND body=?",
    "upsert": (
        "INSERT OR REPLACE INTO positions_daily(day_jd, body, lon, lat, speed)"
        " VALUES (?,?,?,?,?)"
    ),
}


def _connect():
    con = sqlite3.connect(str(DB))
    con.execute(_SQL["init"])
    return con


def _day_jd(jd_ut: float) -> int:
    return int(jd_ut)


def _ensure_swiss_available() -> bool:
    from ..detectors import common as detectors_common  # late import to avoid cycles

    return detectors_common._ensure_swiss()


def get_lon_daily(jd_ut: float, body: str) -> float:
    con = _connect()
    try:
        cur = con.execute(_SQL["get"], (_day_jd(jd_ut), body.lower()))
        row = cur.fetchone()
        if row is not None:
            return float(row[0])
    finally:
        con.close()
    # miss → compute and store
    if not _ensure_swiss_available():
        raise RuntimeError("Swiss ephemeris unavailable for cache compute")
    import swisseph as swe  # type: ignore

    code = {
        "sun": swe.SUN,
        "moon": swe.MOON,
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,
    }[body.lower()]
    adapter = SwissEphemerisAdapter.get_default_adapter()
    sample = adapter.body_position(float(_day_jd(jd_ut)), code, body_name=body.title())
    lon = float(sample.longitude)
    lat = float(sample.latitude)
    speed = float(sample.speed_longitude)
    con = _connect()
    try:
        con.execute(
            _SQL["upsert"],
            (_day_jd(jd_ut), body.lower(), float(lon), float(lat), float(speed)),
        )
        con.commit()
    finally:
        con.close()
    return float(lon)


def warm_daily(bodies: Iterable[str], start_jd: float, end_jd: float) -> int:
    count = 0
    jd = int(start_jd)
    end = int(end_jd)
    while jd <= end:
        for b in bodies:
            _ = get_lon_daily(jd, b)
            count += 1
        jd += 1
    return count


# >>> AUTO-GEN END: positions-cache v1.0
