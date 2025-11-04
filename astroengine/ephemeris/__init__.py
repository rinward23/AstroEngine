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
    "TimeScaleContext",
    "SupportIssue",
    "filter_supported",
]
