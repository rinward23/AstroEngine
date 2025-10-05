"""Operational helper for warming the ephemeris cache used in ops pipelines."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Sequence

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
DEFAULT_WINDOW_DAYS = 7


def _ensure_environment() -> Path:
    """Ensure AstroEngine directories and Swiss ephemeris path are configured."""

    home = Path(os.environ.get("ASTROENGINE_HOME", Path.home() / ".astroengine"))
    home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ASTROENGINE_HOME", str(home))
    os.environ.setdefault("SE_EPHE_PATH", str(Path("datasets/swisseph_stub").resolve()))
    return home


def warm_ephemeris_cache(
    bodies: Sequence[str] = DEFAULT_BODIES,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> tuple[str, str, int]:
    """Warm the daily ephemeris cache for ``bodies`` over ``window_days`` days."""

    if window_days < 1:
        raise ValueError("window_days must be positive")

    _ensure_environment()
    enable_cache(True)

    start = date.today()
    end = start + timedelta(days=window_days - 1)
    start_iso = start.isoformat()
    end_iso = end.isoformat()
    entries = warm_daily(bodies, iso_to_jd(start_iso), iso_to_jd(end_iso))
    return start_iso, end_iso, int(entries)


def main() -> int:
    """CLI entry point used by the Makefile target."""

    start_iso, end_iso, entries = warm_ephemeris_cache()
    print(
        f"Cache warmed [{', '.join(DEFAULT_BODIES)}] for {start_iso} "
        f"→ {end_iso} ({entries} entries)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - operational entry point
    raise SystemExit(main())
