"""Compatibility re-export for :mod:`astroengine.core.api`.

This shim keeps the public import surface stable while the project
transitions to the new module/submodule/channel/subchannel structure.
"""

from __future__ import annotations

from .core import TransitEngine
from .core.api import TransitEvent, TransitScanConfig
from .events import (
    LunationEvent,
    EclipseEvent,
    StationEvent,
    ReturnEvent,
    ProgressionEvent,
    DirectionEvent,
    ProfectionEvent,
)

__all__ = [
    "TransitEvent",
    "TransitScanConfig",
    "TransitEngine",
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",
]
