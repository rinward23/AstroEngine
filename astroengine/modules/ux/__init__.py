"""Placeholder registry entries for user-experience surfaces."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_ux_module"]


def register_ux_module(registry: AstroRegistry) -> None:
    """Reserve module paths for UX overlays and interactive surfaces."""

    module = registry.register_module(
        "ux",
        metadata={
            "description": "Maps, timelines, and plugin panels (placeholder).",
            "status": "planned",
            "notes": "Implementation hooks live in astroengine.ux; data sources must be documented before enabling runtime exports.",
        },
    )

    maps = module.register_submodule(
        "maps",
        metadata={
            "description": "Locational astrology visualisations.",
            "todo": [
                "Document atlas/tz dataset requirements for astrocartography maps",
                "Ensure interactive layers load only verified coordinate data",
            ],
        },
    )
    maps.register_channel(
        "astrocartography",
        metadata={"renderer": "astroengine.ux.maps.astrocartography.render_map"},
    ).register_subchannel(
        "lines",
        metadata={"description": "Placeholder for meridian and parans overlays."},
        payload={
            "implementation": "pending",
            "todo": [
                "Index planetary line datasets for fast lookup",
                "Cross-check map rendering against Solar Fire exports",
            ],
        },
    )

    timelines = module.register_submodule(
        "timelines",
        metadata={
            "description": "Temporal visualisations for outer cycle tracking.",
            "todo": [
                "Store timeline caches in indexed parquet or SQLite tables",
                "Expose API endpoints for streaming real-time updates",
            ],
        },
    )
    timelines.register_channel(
        "outer_cycles",
        metadata={"renderer": "astroengine.ux.timelines.outer_cycles.render_timeline"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Placeholder for cycle overlay timeline exports."},
        payload={
            "implementation": "pending",
            "todo": [
                "Document data provenance for plotted events",
                "Integrate severity bands once scoring outputs are indexed",
            ],
        },
    )

    plugins = module.register_submodule(
        "plugins",
        metadata={
            "description": "Streamlit panels and hook-based extensions.",
            "todo": [
                "List built-in UI panels exposed via astroengine.plugins",
                "Add automated checks ensuring plugin payloads cite their data sources",
            ],
        },
    )
    plugins.register_channel(
        "panels",
        metadata={"registry": "astroengine.ux.plugins"},
    ).register_subchannel(
        "streamlit",
        metadata={"description": "Placeholder for Streamlit-hosted UI panels."},
        payload={
            "implementation": "pending",
            "todo": [
                "Document commands to launch example panels",
                "Track dataset provenance for any panel-derived outputs",
            ],
        },
    )
