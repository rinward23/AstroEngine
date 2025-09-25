"""Utility submodule for AstroEngine."""

from __future__ import annotations

from .detectors import DETECTOR_NAMES, ENGINE_FLAG_MAP
from .io import load_json_document
from .merging import deep_merge
from .target_frames import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    TARGET_FRAME_BODIES,
    available_frames,
    expand_targets,
    frame_body_options,
)

__all__ = [
    "DEFAULT_TARGET_FRAMES",
    "DEFAULT_TARGET_SELECTION",
    "TARGET_FRAME_BODIES",
    "available_frames",
    "expand_targets",
    "frame_body_options",
    "DETECTOR_NAMES",
    "ENGINE_FLAG_MAP",
    "deep_merge",
    "load_json_document",
]
