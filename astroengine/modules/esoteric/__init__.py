"""Registry wiring for esoteric overlays (decans, tarot correspondences)."""

from __future__ import annotations

from ...esoteric import DECANS
from ..registry import AstroRegistry

__all__ = ["register_esoteric_module"]


def register_esoteric_module(registry: AstroRegistry) -> None:
    """Attach esoteric datasets to the shared :class:`AstroRegistry`."""

    module = registry.register_module(
        "esoterica",
        metadata={
            "description": "Occult and initiatory correspondences layered onto natal analytics.",
            "datasets": ["golden_dawn_decans"],
        },
    )

    decans = module.register_submodule(
        "decans",
        metadata={
            "description": "Ten-degree divisions with Chaldean planetary rulers and tarot pips.",
            "division_degrees": 10,
            "total": len(DECANS),
        },
    )

    chaldean = decans.register_channel(
        "chaldean_order",
        metadata={
            "description": "Classical Chaldean sequence starting at 0° Aries.",
            "sources": [
                "Hermetic Order of the Golden Dawn — Book T (c. 1893)",
                "A. E. Waite — Pictorial Key to the Tarot (1910)",
            ],
        },
    )

    chaldean.register_subchannel(
        "golden_dawn_tarot",
        metadata={
            "description": "Golden Dawn pip card titles matched to the 36 decans.",
            "count": len(DECANS),
        },
        payload={"decans": [definition.to_payload() for definition in DECANS]},
    )
