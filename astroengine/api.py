"""Compatibility re-export for :mod:`astroengine.core.api`.

This shim keeps the public import surface stable while the project
transitions to the new module/submodule/channel/subchannel structure.
"""

from __future__ import annotations

from .core.api import TransitEvent, TransitScanConfig

__all__ = ["TransitEvent", "TransitScanConfig"]
