"""Detector toggle metadata shared across CLI and UI surfaces."""

from __future__ import annotations

from ..config.features import (
    EXPERIMENTAL_MODALITIES,
    available_modalities,
)

DETECTOR_NAMES = available_modalities()
EXPERIMENTAL_DETECTOR_NAMES = tuple(sorted(EXPERIMENTAL_MODALITIES))

ENGINE_FLAG_MAP = {
    "lunations": "FEATURE_LUNATIONS",
    "eclipses": "FEATURE_ECLIPSES",
    "stations": "FEATURE_STATIONS",
    "progressions": "FEATURE_PROGRESSIONS",
    "directions": "FEATURE_DIRECTIONS",
    "returns": "FEATURE_RETURNS",
    "profections": "FEATURE_PROFECTIONS",
}

__all__ = ["DETECTOR_NAMES", "EXPERIMENTAL_DETECTOR_NAMES", "ENGINE_FLAG_MAP"]
