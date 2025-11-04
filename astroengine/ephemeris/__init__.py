"""Ephemeris adapters and helpers exposed by :mod:`astroengine`."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

_ADAPTER_ATTRS = {
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefinementError",
    "TimeScaleContext",
}
_REFINEMENT_ATTRS = {
    "SECONDS_PER_DAY",
    "RefineResult",
    "bracket_root",
    "refine_event",
    "refine_root",
}
_SUPPORT_ATTRS = {"SupportIssue", "filter_supported"}
_SWISSEPH_ATTRS = {
    "BodyPosition",
    "EquatorialPosition",
    "FixedStarPosition",
    "HousePositions",
    "RiseTransitResult",
    "SwissEphemerisAdapter",
}
_HOUSE_SYSTEM_ATTRS = {
    "HOUSE_CODE_BYTES_BY_NAME",
    "HOUSE_ALIASES",
    "HOUSE_CODE_BY_NAME",
    "resolve_house_code",
}

__all__ = sorted(
    _ADAPTER_ATTRS
    | _REFINEMENT_ATTRS
    | _SUPPORT_ATTRS
    | _SWISSEPH_ATTRS
    | _HOUSE_SYSTEM_ATTRS
)

_MODULE_BY_ATTR = {
    "astroengine.ephemeris.adapter": _ADAPTER_ATTRS,
    "astroengine.ephemeris.refinement": _REFINEMENT_ATTRS,
    "astroengine.ephemeris.support": _SUPPORT_ATTRS,
    "astroengine.ephemeris.swisseph_adapter": _SWISSEPH_ATTRS,
    "astroengine.ephemeris.house_systems": _HOUSE_SYSTEM_ATTRS,
}


def __getattr__(name: str) -> Any:
    for module_name, attrs in _MODULE_BY_ATTR.items():
        if name in attrs:
            module = import_module(module_name)
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module 'astroengine.ephemeris' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


if TYPE_CHECKING:  # pragma: no cover - import-time cycle guard
    from .adapter import (  # noqa: F401
        EphemerisAdapter,
        EphemerisConfig,
        EphemerisSample,
        ObserverLocation,
        RefinementError,
        TimeScaleContext,
    )
    from .refinement import (  # noqa: F401
        SECONDS_PER_DAY,
        RefineResult,
        bracket_root,
        refine_event,
        refine_root,
    )
    from .support import SupportIssue, filter_supported  # noqa: F401
    from .swisseph_adapter import (  # noqa: F401
        BodyPosition,
        FixedStarPosition,
        HousePositions,
        RiseTransitResult,
        SwissEphemerisAdapter,
    )
    from .house_systems import (  # noqa: F401
        HOUSE_CODE_BYTES_BY_NAME,
        HOUSE_ALIASES,
        HOUSE_CODE_BY_NAME,
        resolve_house_code,
    )
