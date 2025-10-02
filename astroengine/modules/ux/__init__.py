"""Registry metadata for user-experience overlays."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_ux_module"]


def register_ux_module(registry: AstroRegistry) -> None:
    """Reserve module paths for UX overlays and interactive surfaces."""

    module = registry.register_module(
        "ux",
        metadata={
            "description": "Maps, timelines, and plugin panels for runtime overlays.",
            "status": "active",
            "datasets": [
                "datasets/star_names_iau.csv",
                "profiles/base_profile.yaml",
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            ],
            "tests": [
                "tests/test_locational_visualizations.py",
            ],
            "notes": "Overlay helpers rely on Swiss Ephemeris backed data with Solar Fire parity evidence.",
        },
    )

    maps = module.register_submodule(
        "maps",
        metadata={
            "description": "Locational astrology visualisations derived from Solar Fire indexed datasets.",
            "datasets": [
                "datasets/star_names_iau.csv",
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            ],
            "tests": ["tests/test_locational_visualizations.py"],
        },
    )
    astrocartography = maps.register_channel(
        "astrocartography",
        metadata={
            "renderer": "astroengine.ux.maps.astrocartography.astrocartography_lines",
            "local_space": "astroengine.ux.maps.astrocartography.local_space_vectors",
        },
    )
    astrocartography.register_subchannel(
        "lines",
        metadata={
            "description": "Meridian, IC, ASC, and DSC overlays for planetary bodies.",
        },
        payload={
            "resolver": "astroengine.ux.maps.astrocartography.astrocartography_lines",
            "outputs": ["astroengine.ux.maps.MapLine"],
            "datasets": [
                "datasets/star_names_iau.csv",
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            ],
            "tests": ["tests/test_locational_visualizations.py"],
        },
    )
    astrocartography.register_subchannel(
        "local_space",
        metadata={
            "description": "Azimuth/altitude vectors from the observer's location.",
        },
        payload={
            "resolver": "astroengine.ux.maps.astrocartography.local_space_vectors",
            "outputs": ["astroengine.ux.maps.LocalSpaceVector"],
            "datasets": [
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            ],
            "tests": ["tests/test_locational_visualizations.py"],
        },
    )

    timelines = module.register_submodule(
        "timelines",
        metadata={
            "description": "Temporal visualisations for outer cycle tracking.",
            "datasets": [
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
                "rulesets/transit/ingresses.ruleset.md",
            ],
            "tests": ["tests/test_locational_visualizations.py"],
        },
    )
    timelines.register_channel(
        "outer_cycles",
        metadata={
            "resolver": "astroengine.ux.timelines.outer_cycles.outer_cycle_windows",
            "events": "astroengine.ux.timelines.outer_cycles.outer_cycle_events",
        },
    ).register_subchannel(
        "transits",
        metadata={
            "description": "Cycle overlays constructed from Swiss Ephemeris outer planet aspects.",
        },
        payload={
            "resolver": "astroengine.ux.timelines.outer_cycles.outer_cycle_windows",
            "events": "astroengine.ux.timelines.outer_cycles.outer_cycle_events",
            "datasets": [
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
                "profiles/base_profile.yaml",
            ],
            "tests": ["tests/test_locational_visualizations.py"],
        },
    )

    plugins = module.register_submodule(
        "plugins",
        metadata={
            "description": "Streamlit panels and hook-based extensions backed by pluggy.",
            "tests": ["tests/test_locational_visualizations.py"],
            "notes": "Plugin hooks register via astroengine.ux.plugins.setup_cli and must cite dataset provenance.",
        },
    )
    plugins.register_channel(
        "panels",
        metadata={"registry": "astroengine.ux.plugins"},
    ).register_subchannel(
        "streamlit",
        metadata={
            "description": "Streamlit-hosted UX panels exposed via astroengine-streamlit.",
        },
        payload={
            "commands": ["astroengine-streamlit"],
            "hooks": ["astroengine.ux.plugins.setup_cli"],
            "datasets": ["qa/artifacts/solarfire/2025-10-02/cross_engine.json"],
        },
    )
