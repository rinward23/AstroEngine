"""Placeholder registry entries for user-experience surfaces."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_ux_module"]

UX_DOC = "docs/module/ux.md"


def register_ux_module(registry: AstroRegistry) -> None:
    """Reserve module paths for UX overlays and interactive surfaces."""

    module = registry.register_module(
        "ux",
        metadata={
            "description": "Maps, timelines, and plugin panels backed by documented datasets.",
            "documentation": UX_DOC,
            "status": "planned",
        },
    )

    maps = module.register_submodule(
        "maps",
        metadata={
            "description": "Locational astrology visualisations.",
            "docs": ["docs/module/ux/maps.md"],
        },
    )
    maps.register_channel(
        "astrocartography",
        metadata={
            "description": "Astrocartography overlays documented in docs/module/ux/maps.md.",
            "renderer": "astroengine.ux.maps.astrocartography.render_map",
        },
    ).register_subchannel(
        "lines",
        metadata={
            "description": "Meridian and paran line datasets with Solar Fire provenance.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/ux/maps.md",
            "implementation": "pending",
            "datasets": [
                "docs/provenance/solarfire_exports.md",
                "docs/ATLAS_TZ_SPEC.md",
                "datasets/star_names_iau.csv",
            ],
        },
    )

    timelines = module.register_submodule(
        "timelines",
        metadata={
            "description": "Temporal visualisations for outer cycle tracking.",
            "docs": ["docs/module/ux/timelines.md"],
        },
    )
    timelines.register_channel(
        "outer_cycles",
        metadata={
            "description": "Outer cycle timelines documented in docs/module/ux/timelines.md.",
            "renderer": "astroengine.ux.timelines.outer_cycles.render_timeline",
        },
    ).register_subchannel(
        "transits",
        metadata={
            "description": "Cycle overlay timeline exports derived from detector datasets.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/ux/timelines.md",
            "implementation": "pending",
            "datasets": [
                "docs/provenance/solarfire_exports.md",
                "docs/module/core-transit-math.md",
                "docs/module/event-detectors/overview.md",
            ],
        },
    )

    plugins = module.register_submodule(
        "plugins",
        metadata={
            "description": "Streamlit panels and hook-based extensions.",
            "docs": ["docs/module/ux/plugins.md"],
        },
    )
    plugins.register_channel(
        "panels",
        metadata={
            "description": "Streamlit-based panels documented in docs/module/ux/plugins.md.",
            "registry": "astroengine.ux.plugins",
        },
    ).register_subchannel(
        "streamlit",
        metadata={
            "description": "Streamlit-hosted UI panels with documented dataset provenance.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/ux/plugins.md",
            "implementation": "pending",
            "commands": ["astroengine-streamlit"],
            "datasets": [
                "docs/provenance/solarfire_exports.md",
                "docs/ATLAS_TZ_SPEC.md",
                "docs/module/ux/timelines.md",
            ],
        },
    )
