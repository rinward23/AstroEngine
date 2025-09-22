"""Utility submodule for AstroEngine."""

from __future__ import annotations

from .target_frames import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    TARGET_FRAME_BODIES,
    available_frames,
    expand_targets,
    frame_body_options,
)
from .detectors import DETECTOR_NAMES, ENGINE_FLAG_MAP

__all__ = [
    "DEFAULT_TARGET_FRAMES",
    "DEFAULT_TARGET_SELECTION",
    "TARGET_FRAME_BODIES",
    "available_frames",
    "expand_targets",
    "frame_body_options",
    "DETECTOR_NAMES",
    "ENGINE_FLAG_MAP",
]
