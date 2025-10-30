from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any

from .context import (
    ScanFeaturePlan,
    ScanFeatureToggles,
    ScanProfileContext,
    _build_scan_profile_context,
    build_scan_profile_context,
)
from .frames import TargetFrameResolver

if TYPE_CHECKING:  # pragma: no cover
    from .scanning import (
        FEATURE_DIRECTIONS,
        FEATURE_ECLIPSES,
        FEATURE_LUNATIONS,
        FEATURE_PROFECTIONS,
        FEATURE_PROGRESSIONS,
        FEATURE_RETURNS,
        FEATURE_STATIONS,
        FEATURE_TIMELORDS,
        ScanConfig,
        events_to_dicts,
        fast_scan,
        get_active_aspect_angles,
        resolve_provider,
        scan_contacts,
    )

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

_SCANNING_EXPORTS: set[str] = {
    "ScanConfig",
    "events_to_dicts",
    "fast_scan",
    "get_active_aspect_angles",
    "resolve_provider",
    "scan_contacts",
    "FEATURE_LUNATIONS",
    "FEATURE_ECLIPSES",
    "FEATURE_STATIONS",
    "FEATURE_PROGRESSIONS",
    "FEATURE_DIRECTIONS",
    "FEATURE_RETURNS",
    "FEATURE_PROFECTIONS",
    "FEATURE_TIMELORDS",
}


def _load_scanning() -> ModuleType:
    return import_module(".scanning", __name__)


def __getattr__(name: str) -> Any:
    if name in _SCANNING_EXPORTS:
        module = _load_scanning()
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'astroengine.engine' has no attribute '{name}'")


class _EngineModule(ModuleType):
    def __setattr__(self, name: str, value: Any) -> None:
        if name in _SCANNING_EXPORTS:
            module = _load_scanning()
            setattr(module, name, value)
        super().__setattr__(name, value)


_module = sys.modules[__name__]
_module.__class__ = _EngineModule
