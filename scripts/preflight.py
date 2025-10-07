"""Environment preflight check for AstroEngine developers."""

from __future__ import annotations

import platform
from pathlib import Path

from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig


def main() -> None:
    print(f"Python version: {platform.python_version()}")
    try:
        from astroengine.ephemeris.swe import swe

        print(f"pyswisseph version: {swe().__version__}")
    except ModuleNotFoundError:
        print("pyswisseph not installed")

    path = Path.cwd() / "ephemeris"
    config = EphemerisConfig(ephemeris_path=str(path) if path.exists() else None)
    adapter = EphemerisAdapter(config)
    if config.ephemeris_path:
        print(f"Configured Swiss Ephemeris path: {config.ephemeris_path}")
    else:
        print("Swiss Ephemeris path: auto-detected or using fallback (Moshier)")

    cache_dict = getattr(adapter, "_cache", {})
    print(f"Ephemeris cache entries: {len(cache_dict)}")


if __name__ == "__main__":
    main()
