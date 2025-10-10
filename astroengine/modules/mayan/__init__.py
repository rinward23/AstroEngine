"""Register Mayan calendar assets with the :class:`AstroRegistry`."""

from __future__ import annotations

from ...systems.mayan import (
    GMT_CORRELATION,
    HAAB_MONTHS,
    LORDS_OF_NIGHT,
    TZOLKIN_NAMES,
)
from ..registry import AstroModule, AstroRegistry

__all__ = ["register_mayan_module"]


def register_mayan_module(registry: AstroRegistry) -> AstroModule:
    """Attach GMT-correlated Mayan calendar lookups to the registry."""

    module = registry.register_module(
        "mayan",
        metadata={
            "description": "Mayan Long Count, Tzolk'in, and Haab tables",
            "sources": [
                "Goodman, Martínez & Thompson correlation (584283)",
                "Smithsonian Handbook of Maya Glyphs",
            ],
        },
    )

    calendar = module.register_submodule(
        "calendar",
        metadata={"description": "Calendar round naming sequences."},
    )
    calendar.register_channel("tzolkin").register_subchannel(
        "day_names",
        payload={"names": list(TZOLKIN_NAMES)},
    )
    calendar.register_channel("haab").register_subchannel(
        "month_names",
        payload={"months": list(HAAB_MONTHS)},
    )
    calendar.register_channel("lords_of_night").register_subchannel(
        "g_series",
        payload={"sequence": list(LORDS_OF_NIGHT)},
    )

    constants = module.register_submodule(
        "constants",
        metadata={"description": "Correlation constant for Gregorian ↔︎ Long Count conversions."},
    )
    constants.register_channel("correlation").register_subchannel(
        "gmt",
        payload={"julian_day": GMT_CORRELATION},
    )

    return module

