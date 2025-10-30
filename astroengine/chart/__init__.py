"""Chart computation entry points for :mod:`astroengine`."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "AspectHit",
    "ChartLocation",
    "NatalChart",
    "CompositeBodyPosition",
    "CompositeChart",
    "MidpointEntry",
    "CompositePosition",
    "MidpointCompositeChart",
    "TransitContact",
    "TransitScanner",
    "ProgressedChart",
    "ReturnChart",
    "HarmonicChart",
    "HarmonicPosition",
    "DirectedChart",
    "compute_natal_chart",
    "compute_composite_chart",
    "compute_midpoint_tree",
    "compute_midpoint_composite",
    "compute_secondary_progressed_chart",
    "compute_return_chart",
    "compute_harmonic_chart",
    "compute_solar_arc_chart",
]


if TYPE_CHECKING:
    from .composite import (
        CompositeBodyPosition,
        CompositeChart,
        MidpointEntry,
        compute_composite_chart,
        compute_midpoint_tree,
    )
    from .directions import DirectedChart, compute_solar_arc_chart
    from .harmonics import HarmonicChart, HarmonicPosition, compute_harmonic_chart
    from .midpoints import (
        CompositePosition,
        MidpointCompositeChart,
        compute_midpoint_composite,
    )
    from .natal import AspectHit, ChartLocation, NatalChart, compute_natal_chart
    from .progressions import ProgressedChart, compute_secondary_progressed_chart
    from .returns import ReturnChart, compute_return_chart
    from .transits import TransitContact, TransitScanner

_LAZY_SUBMODULES: dict[str, tuple[str, ...]] = {
    "composite": (
        "CompositeBodyPosition",
        "CompositeChart",
        "MidpointEntry",
        "compute_composite_chart",
        "compute_midpoint_tree",
    ),
    "directions": ("DirectedChart", "compute_solar_arc_chart"),
    "harmonics": ("HarmonicChart", "HarmonicPosition", "compute_harmonic_chart"),
    "midpoints": (
        "CompositePosition",
        "MidpointCompositeChart",
        "compute_midpoint_composite",
    ),
    "natal": ("AspectHit", "ChartLocation", "NatalChart", "compute_natal_chart"),
    "progressions": ("ProgressedChart", "compute_secondary_progressed_chart"),
    "returns": ("ReturnChart", "compute_return_chart"),
    "transits": ("TransitContact", "TransitScanner"),
}

_LAZY_ATTRS: dict[str, tuple[str, str]] = {}
for _module, _names in _LAZY_SUBMODULES.items():
    for _name in _names:
        _LAZY_ATTRS[_name] = (_module, _name)


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
    return sorted(set(__all__) | set(_LAZY_ATTRS) | set(globals().keys()))
