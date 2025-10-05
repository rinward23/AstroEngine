"""Accuracy profiles governing scan precision/performance trade-offs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True)
class AccuracyProfile:
    """Parameters describing a precision budget for scan routines."""

    tol_arcsec: float
    """Target refinement tolerance expressed in arcseconds."""

    max_iter: int
    """Maximum refinement iterations to attempt."""

    coarse_step_sec: float
    """Baseline coarse sampling cadence expressed in seconds."""


ACCURACY_PROFILES: dict[Literal["fast", "default", "high"], AccuracyProfile] = {
    "fast": AccuracyProfile(tol_arcsec=0.5, max_iter=4, coarse_step_sec=120.0),
    "default": AccuracyProfile(tol_arcsec=0.2, max_iter=8, coarse_step_sec=60.0),
    "high": AccuracyProfile(tol_arcsec=0.05, max_iter=16, coarse_step_sec=30.0),
}


__all__ = ["AccuracyProfile", "ACCURACY_PROFILES"]
