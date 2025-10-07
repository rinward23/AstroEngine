"""Operational helper for warming the ephemeris cache used in ops pipelines."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from ..cache.positions_cache import warm_daily
from ..detectors.common import enable_cache, iso_to_jd

DEFAULT_BODIES: Sequence[str] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)
DEFAULT_START = date(1900, 1, 1)
DEFAULT_END = date(2100, 12, 31)


def _ensure_environment() -> Path:
    """Ensure AstroEngine directories and Swiss ephemeris path are configured."""

    home = Path(os.environ.get("ASTROENGINE_HOME", Path.home() / ".astroengine"))
    home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ASTROENGINE_HOME", str(home))
    os.environ.setdefault("SE_EPHE_PATH", str(Path("datasets/swisseph_stub").resolve()))
    return home


def _parse_date_env(name: str, default: date) -> date:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be YYYY-MM-DD") from exc


def _parse_bodies_env() -> Sequence[str]:
    raw = os.environ.get("AE_WARM_BODIES")
    if not raw:
        return DEFAULT_BODIES
    entries = [token.strip() for token in raw.split(",") if token.strip()]
    return tuple(entries) if entries else DEFAULT_BODIES


def warm_ephemeris_cache(
    bodies: Sequence[str] = DEFAULT_BODIES,
    *,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
) -> tuple[str, str, int]:
    """Warm the daily ephemeris cache between ``start`` and ``end`` (inclusive)."""

    if end < start:
        raise ValueError("end date must not be before start date")

    _ensure_environment()
    enable_cache(True)

    start_iso = start.isoformat()
    end_iso = end.isoformat()
    entries = warm_daily(bodies, iso_to_jd(start_iso), iso_to_jd(end_iso))
    return start_iso, end_iso, int(entries)


def main() -> int:
    """CLI entry point used by the Makefile target."""

    bodies = _parse_bodies_env()
    start = _parse_date_env("AE_WARM_START", DEFAULT_START)
    end = _parse_date_env("AE_WARM_END", DEFAULT_END)
    start_iso, end_iso, entries = warm_ephemeris_cache(bodies, start=start, end=end)
    print(
        f"Cache warmed [{', '.join(bodies)}] for {start_iso} "
        f"→ {end_iso} ({entries} entries)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - operational entry point
    raise SystemExit(main())
