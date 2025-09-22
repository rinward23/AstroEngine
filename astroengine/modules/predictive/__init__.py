"""Registry wiring for predictive and derived chart datasets."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_predictive_module"]


def register_predictive_module(registry: AstroRegistry) -> None:
    """Attach predictive chart capabilities to the shared registry."""

    module = registry.register_module(
        "predictive",
        metadata={
            "description": "Progressions, returns, and derived chart utilities backed by Swiss ephemeris data.",
        },
    )

    progressions = module.register_submodule(
        "progressions",
        metadata={
            "techniques": ["secondary"],
            "cadence": "annual",
        },
    )
    progressions.register_channel(
        "secondary",
        metadata={
            "description": "Secondary progressions computed via day-for-a-year mapping.",
            "sources": ["Swiss Ephemeris"],
        },
    )

    directions = module.register_submodule(
        "directions",
        metadata={"techniques": ["solar_arc"]},
    )
    directions.register_channel(
        "solar_arc",
        metadata={
            "description": "Solar arc directions using progressed Sun motion applied to natal bodies.",
            "sources": ["Swiss Ephemeris"],
        },
    )

    returns = module.register_submodule(
        "returns",
        metadata={"kinds": ["solar", "lunar"]},
    )
    returns.register_channel(
        "solar",
        metadata={"description": "Solar return computed when the Sun matches its natal longitude."},
    )
    returns.register_channel(
        "lunar",
        metadata={"description": "Lunar return computed when the Moon matches its natal longitude."},
    )

    derived = module.register_submodule(
        "derived_charts",
        metadata={"description": "Midpoints, harmonics, and other synthetic charts built from natal data."},
    )
    derived.register_channel(
        "harmonics",
        metadata={"description": "Multiplicative harmonic overlays (e.g., 5th, 7th)."},
    )
    derived.register_channel(
        "midpoints",
        metadata={"description": "Midpoint composites averaging two natal charts."},
    )
