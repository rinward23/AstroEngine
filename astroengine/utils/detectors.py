"""Detector toggle metadata shared across CLI and UI surfaces."""

from __future__ import annotations

DETECTOR_NAMES = (
    "lunations",
    "eclipses",
    "stations",
    "progressions",
    "directions",
    "returns",
    "profections",
    "timelords",
    "midpoints",
    "antiscia",
)

ENGINE_FLAG_MAP = {
    "lunations": "FEATURE_LUNATIONS",
    "eclipses": "FEATURE_ECLIPSES",
    "stations": "FEATURE_STATIONS",
    "progressions": "FEATURE_PROGRESSIONS",
    "directions": "FEATURE_DIRECTIONS",
    "returns": "FEATURE_RETURNS",
    "profections": "FEATURE_PROFECTIONS",
}

__all__ = ["DETECTOR_NAMES", "ENGINE_FLAG_MAP"]
