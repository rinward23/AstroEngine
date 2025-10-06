"""Return chart computation primitives for AstroEngine's predictive stack."""

from __future__ import annotations

from .attach import attach_aspects_to_natal, attach_transiting_aspects
from .finder import (
    ReturnInstant,
    ReturnNotFoundError,
    find_return_instant,
    guess_window,
)
from .scan import (
    AttachOptions,
    GeoLoc,
    NatalCtx,
    PositionSnapshot,
    ReturnHit,
    ScanOptions,
    scan_returns,
)

__all__ = [
    "AttachOptions",
    "GeoLoc",
    "NatalCtx",
    "PositionSnapshot",
    "ReturnHit",
    "ReturnInstant",
    "ReturnNotFoundError",
    "ScanOptions",
    "attach_aspects_to_natal",
    "attach_transiting_aspects",
    "find_return_instant",
    "guess_window",
    "scan_returns",
]
