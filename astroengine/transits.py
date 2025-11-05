"""Transit and ephemeris interfaces exposed for public consumption."""

from __future__ import annotations

from .core import (
    AngleTracker,
    TransitEngine,
    TransitEngineConfig,
    TransitEvent,
    TransitScanConfig,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
    to_tt,
)
from .ephemeris.adapter import (
    EphemerisAdapter,
    EphemerisConfig,
    EphemerisSample,
    ObserverLocation,
    RefinementError,
    TimeScaleContext,
)
from .ephemeris.refinement import (
    RefineResult,
    SECONDS_PER_DAY,
    bracket_root,
    refine_event,
    refine_root,
)
from .ephemeris.swisseph_adapter import SwissEphemerisAdapter

__all__ = [
    "AngleTracker",
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefineResult",
    "RefinementError",
    "SwissEphemerisAdapter",
    "TimeScaleContext",
    "SECONDS_PER_DAY",
    "TransitEngine",
    "TransitEngineConfig",
    "TransitEvent",
    "TransitScanConfig",
    "bracket_root",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "refine_event",
    "refine_root",
    "to_tt",
]
