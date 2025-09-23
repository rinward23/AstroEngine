"""Registry wiring for generational cycles and astrological ages."""

from __future__ import annotations

from ...ephemeris.sidereal import DEFAULT_SIDEREAL_AYANAMSHA
from ..registry import AstroRegistry

__all__ = ["register_cycles_module"]


def register_cycles_module(registry: AstroRegistry) -> None:
    """Attach cycle analytics metadata to the shared registry."""

    module = registry.register_module(
        "cycles",
        metadata={
            "description": "Generational outer-planet analytics, fixed-star parans, and astrological age tooling.",
        },
    )

    fixedstars = module.register_submodule(
        "fixedstars",
        metadata={
            "description": "Horizon-based star analyses referencing the IAU bright-star dataset.",
            "datasets": ["star_names_iau.csv"],
        },
    )

    parans = fixedstars.register_channel(
        "parans",
        metadata={
            "description": "Simultaneous angularity detection for stars and planets using Skyfield.",
            "sources": ["IAU Star Names", "JPL DE ephemerides"],
        },
    )
    parans.register_subchannel(
        "daily_windows",
        metadata={
            "description": "Daily parans across ASC/MC/DESC/IC angles with configurable thresholds.",
            "interfaces": ["astroengine.fixedstars.parans.compute_star_parans"],
        },
    )

    heliacal = fixedstars.register_channel(
        "heliacal",
        metadata={
            "description": "Heliacal rising/setting visibility estimates derived from twilight scans.",
            "sources": ["IAU Star Names", "JPL DE ephemerides"],
        },
    )
    heliacal.register_subchannel(
        "visibility",
        metadata={
            "description": "Sun-altitude gated visibility metrics for dawn/dusk windows.",
            "interfaces": ["astroengine.fixedstars.parans.compute_heliacal_phases"],
        },
    )

    generational = module.register_submodule(
        "generational_cycles",
        metadata={
            "description": "Outer-planet separations and wave diagnostics for mundane dashboards.",
            "bodies": ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"],
        },
    )
    outer_planets = generational.register_channel(
        "outer_planets",
        metadata={
            "description": "Timelines and derivative measures for outer-planet pairs.",
            "sources": ["Swiss Ephemeris"],
        },
    )
    outer_planets.register_subchannel(
        "timeline",
        metadata={
            "description": "Pairwise separation samples with aspect tagging for dashboard visualisations.",
            "interfaces": ["astroengine.cycles.outer_cycle_timeline"],
        },
    )
    outer_planets.register_subchannel(
        "neptune_pluto_wave",
        metadata={
            "description": "Neptune–Pluto wave analysis with rate-of-change metrics.",
            "interfaces": ["astroengine.cycles.neptune_pluto_wave"],
        },
    )

    ages = module.register_submodule(
        "astrological_ages",
        metadata={
            "description": "Aries ingress ayanamsha tracking for astrological age research.",
            "default_ayanamsha": DEFAULT_SIDEREAL_AYANAMSHA,
        },
    )
    sidereal = ages.register_channel(
        "sidereal_projection",
        metadata={
            "description": "Projection of the tropical vernal point into sidereal longitudes.",
            "sources": ["Swiss Ephemeris"],
        },
    )
    sidereal.register_subchannel(
        "series",
        metadata={
            "description": "Per-year Aries ingress ayanamsha offsets and derived age sign.",
            "interfaces": ["astroengine.cycles.compute_age_series"],
        },
    )
    sidereal.register_subchannel(
        "boundaries",
        metadata={
            "description": "Astrological age boundaries derived from sidereal ingress data.",
            "interfaces": ["astroengine.cycles.derive_age_boundaries"],
        },
    )

