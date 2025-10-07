"""House computation helpers for symbolic techniques."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import guarded for optional swe
    from ...ephemeris import HousePositions

__all__ = ["HouseOptions", "compute_angles_houses"]


@dataclass(frozen=True)
class HouseOptions:
    system: str = "placidus"


def compute_angles_houses(
    moment: object,
    loc_lat: float,
    loc_lon: float,
    *,
    options: HouseOptions | None = None,
) -> HousePositions:
    """Compute houses for the requested instant and location."""

    from ...ephemeris import SwissEphemerisAdapter

    adapter = SwissEphemerisAdapter.get_default_adapter()
    opts = options or HouseOptions()
    if not hasattr(moment, "jd_utc"):
        from ...core.time import to_tt

        moment = to_tt(moment)
    return adapter.houses(moment.jd_utc, loc_lat, loc_lon, system=opts.system)
