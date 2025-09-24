"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import sys
from types import ModuleType

from .context import (
    ScanFeaturePlan,
    ScanFeatureToggles,
    ScanProfileContext,
    _build_scan_profile_context,
    build_scan_profile_context,
)
from .frames import TargetFrameResolver
from . import scanning as _scanning
from .scanning import (
    ScanConfig,
    events_to_dicts,
    fast_scan,
    get_active_aspect_angles,
    resolve_provider,
    scan_contacts,
)

_FEATURE_ATTRS = {
    "FEATURE_LUNATIONS",
    "FEATURE_ECLIPSES",
    "FEATURE_STATIONS",
    "FEATURE_PROGRESSIONS",
    "FEATURE_DIRECTIONS",
    "FEATURE_RETURNS",
    "FEATURE_PROFECTIONS",
    "FEATURE_TIMELORDS",
}


def __getattr__(name: str):
    if name in _FEATURE_ATTRS:
        return getattr(_scanning, name)
    raise AttributeError(f"module 'astroengine.engine' has no attribute '{name}'")


class _EngineModule(ModuleType):
    def __setattr__(self, name, value):
        if name in _FEATURE_ATTRS:
            setattr(_scanning, name, value)
        super().__setattr__(name, value)


_module = sys.modules[__name__]
_module.__class__ = _EngineModule
for _attr in _FEATURE_ATTRS:
    setattr(_module, _attr, getattr(_scanning, _attr))

__all__ = [
    "events_to_dicts",
    "scan_contacts",
    "get_active_aspect_angles",
    "resolve_provider",
    "fast_scan",
    "ScanConfig",
    "TargetFrameResolver",
    "ScanFeaturePlan",
    "ScanFeatureToggles",
    "ScanProfileContext",
    "build_scan_profile_context",
    "_build_scan_profile_context",
    "FEATURE_LUNATIONS",
    "FEATURE_ECLIPSES",
    "FEATURE_STATIONS",
    "FEATURE_PROGRESSIONS",
    "FEATURE_DIRECTIONS",
    "FEATURE_RETURNS",
    "FEATURE_PROFECTIONS",
    "FEATURE_TIMELORDS",
]

