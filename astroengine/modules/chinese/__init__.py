"""Register Chinese calendrical assets with the :class:`AstroRegistry`."""

from __future__ import annotations

from ...systems.chinese import (
    EARTHLY_BRANCHES,
    FIVE_ELEMENTS,
    HEAVENLY_STEMS,
    LUNAR_INFO,
    SHENGXIAO_ANIMALS,
)
from ..registry import AstroModule, AstroRegistry

__all__ = ["register_chinese_module"]


def register_chinese_module(registry: AstroRegistry) -> AstroModule:
    """Attach Chinese lunisolar lookup tables and symbolism metadata."""

    module = registry.register_module(
        "chinese",
        metadata={
            "description": "Chinese lunisolar calendar and BaZi symbolism",
            "sources": [
                "Hong Kong Observatory — Chinese Calendar Data (1900–2099)",
                "Helmer Aslaksen, The Mathematics of the Chinese Calendar (2010)",
            ],
        },
    )

    calendar = module.register_submodule(
        "calendar",
        metadata={
            "description": "Bit-packed lunar month metadata derived from Hong Kong Observatory tables.",
        },
    )
    calendar.register_channel(
        "lunisolar",
        metadata={"coverage": "1900-2099"},
    ).register_subchannel(
        "observatory_table",
        metadata={"encoding": "LunarInfo"},
        payload={
            "start_year": 1900,
            "end_year": 2099,
            "lunar_info": list(LUNAR_INFO),
        },
    )

    zodiac = module.register_submodule(
        "zodiac",
        metadata={"description": "Sexagenary stems, branches, and zodiac animal mappings."},
    )
    zodiac.register_channel("stems").register_subchannel(
        "ten_heavenly",
        payload={"stems": list(HEAVENLY_STEMS)},
    )
    zodiac.register_channel("branches").register_subchannel(
        "twelve_earthly",
        payload={
            "branches": list(EARTHLY_BRANCHES),
            "animals": list(SHENGXIAO_ANIMALS),
        },
    )

    symbolism = module.register_submodule(
        "symbolism",
        metadata={"description": "Wu Xing associations used in Chinese elemental astrology."},
    )
    symbolism.register_channel("elements").register_subchannel(
        "wu_xing",
        payload={"meanings": dict(FIVE_ELEMENTS)},
    )

    return module

