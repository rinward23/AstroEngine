# >>> AUTO-GEN BEGIN: se-fixedstars-adapter v1.0
"""Swiss Ephemeris fixed stars adapter (guarded, minimal).

Exposes get_star_lonlat(name, jd_ut). Requires pyswisseph and star names
supported by Swiss Ephemeris (e.g., "Aldebaran", "Regulus").
"""
from __future__ import annotations

from ..ephemeris import SwissEphemerisAdapter

_ADAPTER: SwissEphemerisAdapter | None = None


def _require_adapter() -> SwissEphemerisAdapter:
    global _ADAPTER
    if _ADAPTER is not None:
        return _ADAPTER
    try:
        _ADAPTER = SwissEphemerisAdapter.get_default_adapter()
    except Exception as exc:  # pragma: no cover - guarded in calling code
        raise RuntimeError(
            "pyswisseph not available; install astroengine[ephem]"
        ) from exc
    return _ADAPTER


def get_star_lonlat(name: str, jd_ut: float) -> tuple[float, float]:
    adapter = _require_adapter()
    position = adapter.fixed_star(name, jd_ut)
    return float(position.longitude), float(position.latitude)


# >>> AUTO-GEN END: se-fixedstars-adapter v1.0
