"""Registry wiring for mundane ingress analytics."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_mundane_module"]


def register_mundane_module(registry: AstroRegistry) -> None:
    """Register mundane ingress channels with provenance metadata."""

    module = registry.register_module(
        "mundane",
        metadata={
            "description": "Solar ingress charts and mundane overlays validated against Solar Fire exports.",
            "status": "active",
            "datasets": [
                "rulesets/transit/ingresses.ruleset.md",
                "docs/module/event-detectors/overview.md",
            ],
            "tests": [
                "tests/test_ingresses_mundane.py",
                "tests/test_cli.py",
            ],
        },
    )

    ingress = module.register_submodule(
        "ingress",
        metadata={
            "description": "Solar ingress charts with aspect overlays and natal comparisons.",
            "datasets": [
                "rulesets/transit/ingresses.ruleset.md",
                "profiles/base_profile.yaml",
            ],
            "tests": ["tests/test_ingresses_mundane.py"],
        },
    )

    charts = ingress.register_channel(
        "solar_ingress",
        metadata={
            "description": "Ingress charts for each zodiac sign computed via Swiss Ephemeris.",
            "source_functions": [
                "astroengine.mundane.ingress.compute_solar_ingress_chart",
                "astroengine.mundane.ingress.compute_solar_quartet",
            ],
        },
    )
    charts.register_subchannel(
        "sign_charts",
        metadata={"description": "Compute ingress chart for a specific sign boundary."},
        payload={
            "resolver": "astroengine.mundane.ingress.compute_solar_ingress_chart",
            "event_type": "astroengine.mundane.ingress.SolarIngressChart",
            "datasets": [
                "Swiss Ephemeris",
                "rulesets/transit/ingresses.ruleset.md",
                "profiles/base_profile.yaml",
            ],
            "tests": ["tests/test_ingresses_mundane.py"],
            "notes": "Charts include ingress aspects and optional natal overlays with provenance hashes.",
        },
    )
    charts.register_subchannel(
        "seasonal_quartet",
        metadata={"description": "Package the Aries/Cancer/Libra/Capricorn ingress charts."},
        payload={
            "resolver": "astroengine.mundane.ingress.compute_solar_quartet",
            "event_type": "list[astroengine.mundane.ingress.SolarIngressChart]",
            "datasets": [
                "Swiss Ephemeris",
                "rulesets/transit/ingresses.ruleset.md",
            ],
            "tests": ["tests/test_ingresses_mundane.py"],
            "notes": "Quartet exports return sequential ingress charts with shared aspect metadata.",
        },
    )

    cycles = module.register_submodule(
        "cycles",
        metadata={
            "description": "Outer planet cycle analytics aligned with dynamic aspect searches.",
            "datasets": ["docs/module/mundane/submodules/outer_cycle_analytics.md"],
            "tests": ["tests/test_aspect_search.py"],
        },
    )
    cycles.register_channel(
        "search",
        metadata={
            "description": "Scan mundane cycles using astroengine.core.aspects_plus.search helpers.",
        },
    ).register_subchannel(
        "time_range",
        metadata={
            "description": "Time-windowed outer planet aspect searches including harmonic expansions.",
        },
        payload={
            "resolver": "astroengine.mundane.cycles.search",
            "datasets": ["docs/module/mundane/submodules/outer_cycle_analytics.md"],
        },
    )

    module.register_submodule(
        "aspects",
        metadata={
            "description": "Mundane aspect scoring for ingress charts and natal overlays.",
            "datasets": ["rulesets/transit/scan.ruleset.md"],
            "notes": "Aspects are generated directly by astroengine.mundane.ingress via OrbCalculator thresholds.",
        },
    )
