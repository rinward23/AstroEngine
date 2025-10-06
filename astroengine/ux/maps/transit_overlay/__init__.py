"""Transit ↔ natal heliocentric overlay utilities."""
from __future__ import annotations

from .aspects import TRANSIT_ORB_LIMITS, AspectHit, compute_transit_aspects
from .engine import (
    OverlayBodyState,
    OverlayFrame,
    OverlayOptions,
    OverlayRequest,
    TransitOverlayResult,
    compute_overlay_frames,
)
from .layout import BREAKS, scale_au
from .svg import render_overlay_svg

__all__ = [
    "AspectHit",
    "TRANSIT_ORB_LIMITS",
    "OverlayBodyState",
    "OverlayFrame",
    "OverlayOptions",
    "OverlayRequest",
    "TransitOverlayResult",
    "compute_overlay_frames",
    "compute_transit_aspects",
    "render_overlay_svg",
    "BREAKS",
    "scale_au",
]
