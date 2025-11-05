"""Ephemeris adapters and helpers exposed by :mod:`astroengine`."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "BodyPosition",
    "EquatorialPosition",
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "FixedStarPosition",
    "HousePositions",
    "ObserverLocation",
    "RefineResult",
    "RefinementError",
    "RiseTransitResult",
    "SECONDS_PER_DAY",
    "SwissEphemerisAdapter",
    "SupportIssue",
    "TimeScaleContext",
    "bracket_root",
    "filter_supported",
    "refine_event",
    "refine_root",
]

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for static analysis
    from .adapter import (
        EphemerisAdapter,
        EphemerisConfig,
        EphemerisSample,
        ObserverLocation,
        RefinementError,
        TimeScaleContext,
    )
    from .refinement import (
        RefineResult,
        SECONDS_PER_DAY,
        bracket_root,
        refine_event,
        refine_root,
    )
    from .support import SupportIssue, filter_supported
    from .swisseph_adapter import (
        BodyPosition,
        EquatorialPosition,
        FixedStarPosition,
        HousePositions,
        RiseTransitResult,
        SwissEphemerisAdapter,
    )

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "EphemerisAdapter": ("adapter", "EphemerisAdapter"),
    "EphemerisConfig": ("adapter", "EphemerisConfig"),
    "EphemerisSample": ("adapter", "EphemerisSample"),
    "ObserverLocation": ("adapter", "ObserverLocation"),
    "RefinementError": ("adapter", "RefinementError"),
    "TimeScaleContext": ("adapter", "TimeScaleContext"),
    "RefineResult": ("refinement", "RefineResult"),
    "SECONDS_PER_DAY": ("refinement", "SECONDS_PER_DAY"),
    "bracket_root": ("refinement", "bracket_root"),
    "refine_event": ("refinement", "refine_event"),
    "refine_root": ("refinement", "refine_root"),
    "SupportIssue": ("support", "SupportIssue"),
    "filter_supported": ("support", "filter_supported"),
    "BodyPosition": ("swisseph_adapter", "BodyPosition"),
    "EquatorialPosition": ("swisseph_adapter", "EquatorialPosition"),
    "FixedStarPosition": ("swisseph_adapter", "FixedStarPosition"),
    "HousePositions": ("swisseph_adapter", "HousePositions"),
    "RiseTransitResult": ("swisseph_adapter", "RiseTransitResult"),
    "SwissEphemerisAdapter": ("swisseph_adapter", "SwissEphemerisAdapter"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals().keys()))
