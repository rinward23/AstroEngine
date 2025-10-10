"""Registry wiring for Chinese astrology engines."""

from __future__ import annotations

from ..registry import AstroModule, AstroRegistry

__all__ = ["register_chinese_module"]


DOC_PATH = "docs/module/chinese_astrology.md"
PROFILE_PATH = "profiles/domains/chinese.yaml"


def register_chinese_module(registry: AstroRegistry) -> AstroModule:
    """Attach Chinese astrology chart builders to the registry."""

    module = registry.register_module(
        "chinese",
        metadata={
            "description": "Four Pillars (BaZi) and Zi Wei Dou Shu chart computation.",
            "documentation": DOC_PATH,
            "profiles": [PROFILE_PATH],
        },
    )

    bazi = module.register_submodule(
        "four_pillars",
        metadata={
            "description": "Sexagenary pillar calculations for BaZi charts.",
            "api": "astroengine.chinese.compute_four_pillars",
        },
    )
    bazi.register_channel(
        "engines",
        metadata={"description": "Primary BaZi computation routine."},
    ).register_subchannel(
        "default",
        metadata={"tests": ["tests/chinese/test_four_pillars.py"]},
        payload={"callable": "astroengine.chinese.compute_four_pillars"},
    )

    zi_wei = module.register_submodule(
        "zi_wei_dou_shu",
        metadata={
            "description": "Twelve-palace Zi Wei Dou Shu star placement.",
            "api": "astroengine.chinese.compute_zi_wei_chart",
        },
    )
    zi_wei.register_channel(
        "engines",
        metadata={"description": "Primary Zi Wei chart routine."},
    ).register_subchannel(
        "default",
        metadata={"tests": ["tests/chinese/test_zi_wei.py"]},
        payload={"callable": "astroengine.chinese.compute_zi_wei_chart"},
    )

    return module
