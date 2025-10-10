"""Register Tibetan rabjung data with the :class:`AstroRegistry`."""

from __future__ import annotations

from ...systems.tibetan import RABJUNG_TRIGRAMS, TIBETAN_ANIMALS, TIBETAN_ELEMENTS
from ..registry import AstroModule, AstroRegistry

__all__ = ["register_tibetan_module"]


def register_tibetan_module(registry: AstroRegistry) -> AstroModule:
    """Publish Tibetan rabjung symbolism tables."""

    module = registry.register_module(
        "tibetan",
        metadata={
            "description": "Rabjung cycle, Parkha trigrams, and elemental correspondences",
            "sources": [
                "Philippe Cornu, Tibetan Astrology (Snow Lion, 2002)",
                "Druk Henkel Almanac — Department of Culture, Bhutan",
            ],
        },
    )

    symbolism = module.register_submodule(
        "symbolism",
        metadata={"description": "Elemental, animal, and parkha correspondences."},
    )
    symbolism.register_channel("elements").register_subchannel(
        "five",
        payload={"meanings": dict(TIBETAN_ELEMENTS)},
    )
    symbolism.register_channel("animals").register_subchannel(
        "twelve_year_cycle",
        payload={"animals": list(TIBETAN_ANIMALS)},
    )
    symbolism.register_channel("parkha").register_subchannel(
        "trigrams",
        payload={"meanings": dict(RABJUNG_TRIGRAMS)},
    )

    return module

