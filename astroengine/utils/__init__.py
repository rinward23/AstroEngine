"""Utility submodule for AstroEngine.

The module previously imported every helper it re-exported at import time.
That eager loading triggered a circular dependency during
``import astroengine`` because ``astroengine.utils.detectors`` depends on the
configuration subsystem which itself imports scoring policies that require
``deep_merge`` from this package.  To keep the public surface stable while
avoiding the circular import we lazily load detector metadata using
``__getattr__``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

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

_LAZY_ATTRS = {
    "DETECTOR_NAMES": "detectors",
    "ENGINE_FLAG_MAP": "detectors",
    "EXPERIMENTAL_DETECTOR_NAMES": "detectors",
}

__all__ = [
    "DEFAULT_TARGET_FRAMES",
    "DEFAULT_TARGET_SELECTION",
    "TARGET_FRAME_BODIES",
    "available_frames",
    "expand_targets",
    "frame_body_options",
    "DETECTOR_NAMES",
    "ENGINE_FLAG_MAP",
    "EXPERIMENTAL_DETECTOR_NAMES",
    "deep_merge",
    "load_json_document",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - simple delegation
    """Lazily resolve attributes that would otherwise trigger cycles."""

    module_name = _LAZY_ATTRS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:  # pragma: no cover - reflective helper
    """Expose lazy attributes to :func:`dir` callers."""

    return sorted(set(__all__) | set(globals().keys()) | set(_LAZY_ATTRS))
