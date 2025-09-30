"""Register Jyotish rule assets with the :class:`AstroRegistry`."""

from __future__ import annotations

from ...jyotish.data import (
    COMBUSTION_LIMITS,
    DEBILITATION_SIGNS,
    EXALTATION_SIGNS,
    HOUSE_KARAKAS,
    MOOLATRIKONA_SPANS,
    PLANETARY_WAR_BRIGHTNESS,
    PLANETARY_WAR_PARTICIPANTS,
    SIGN_CO_LORDS,
    SIGN_LORDS,
    SRISHTI_ASPECT_OFFSETS,
)
from ..registry import AstroModule, AstroRegistry

__all__ = ["register_jyotish_module"]


def register_jyotish_module(registry: AstroRegistry) -> AstroModule:
    """Attach the bundled Jyotish rule metadata to ``registry``."""

    module = registry.register_module(
        "jyotish",
        metadata={
            "description": "Classical Parasara house lords, karakas, and dignity rules",
            "sources": [
                "Brihat Parashara Hora Shastra (Kapoor translation, 1967)",
                "B. V. Raman — Graha and Bhava Balas (1984)",
            ],
        },
    )

    houses = module.register_submodule(
        "houses",
        metadata={
            "description": "Ruling lords and natural significators for each bhava.",
        },
    )
    lords_channel = houses.register_channel(
        "lords",
        metadata={"description": "Classical sign and co-lord assignments."},
    )
    lords_channel.register_subchannel(
        "parasara",
        metadata={"include_co_lords": False},
        payload={
            "sign_lords": {sign: list(lords) for sign, lords in SIGN_LORDS.items()},
            "co_lords": {sign: list(lords) for sign, lords in SIGN_CO_LORDS.items()},
        },
    )
    houses.register_channel(
        "karakas",
        metadata={"description": "Natural significators mapped to houses."},
    ).register_subchannel(
        "parasara",
        metadata={"count": len(HOUSE_KARAKAS)},
        payload={"house_karakas": {house: list(planets) for house, planets in HOUSE_KARAKAS.items()}},
    )

    strength = module.register_submodule(
        "strength",
        metadata={"description": "Dignity and combustion reference tables."},
    )
    dignity_channel = strength.register_channel(
        "dignity",
        metadata={"description": "Exaltation, debilitation, and moolatrikona spans."},
    )
    dignity_channel.register_subchannel(
        "sign_status",
        metadata={"planets": len(EXALTATION_SIGNS)},
        payload={
            "exaltation": dict(EXALTATION_SIGNS),
            "debilitation": dict(DEBILITATION_SIGNS),
            "moolatrikona": {
                planet: {
                    "sign": sign,
                    "start_deg": start,
                    "end_deg": end,
                }
                for planet, (sign, start, end) in MOOLATRIKONA_SPANS.items()
            },
        },
    )
    strength.register_channel(
        "combustion",
        metadata={"description": "Solar combustion orbs in degrees."},
    ).register_subchannel(
        "raman_tables",
        metadata={"planets": len(COMBUSTION_LIMITS)},
        payload={"limits": dict(COMBUSTION_LIMITS)},
    )

    aspects = module.register_submodule(
        "aspects",
        metadata={"description": "Whole-sign drishti and graha yuddha rules."},
    )
    aspects.register_channel(
        "srishti",
        metadata={"description": "Parasara special aspects."},
    ).register_subchannel(
        "classical",
        metadata={},
        payload={"offsets": {planet: list(offsets) for planet, offsets in SRISHTI_ASPECT_OFFSETS.items()}},
    )
    aspects.register_channel(
        "graha_yuddha",
        metadata={"description": "Planetary war participants and tie-break order."},
    ).register_subchannel(
        "classical",
        metadata={"participants": len(PLANETARY_WAR_PARTICIPANTS)},
        payload={
            "participants": list(PLANETARY_WAR_PARTICIPANTS),
            "brightness_priority": dict(PLANETARY_WAR_BRIGHTNESS),
        },
    )

    return module
