"""Coarse contact detectors for declination and antiscia mirrors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .providers import EphemerisProvider

__all__ = [
    "CoarseHit",
    "detect_decl_contacts",
    "detect_antiscia_contacts",
]


@dataclass
class CoarseHit:
    kind: str
    when_iso: str
    moving: str
    target: str
    delta: float
    applying_or_separating: str


_EPS = 1e-9


def _phase(prev_abs: float | None, current_abs: float) -> str:
    if prev_abs is None or current_abs <= prev_abs + _EPS:
        return "applying"
    return "separating"


def detect_decl_contacts(
    provider: EphemerisProvider,
    ticks: Iterable[str],
    moving: str,
    target: str,
    parallel_orb: float,
    contra_orb: float,
) -> List[CoarseHit]:
    hits: List[CoarseHit] = []
    prev_parallel: float | None = None
    prev_contra: float | None = None
    for iso in ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        moving_pos = positions.get(moving)
        target_pos = positions.get(target)
        if not moving_pos or not target_pos:
            continue

        delta_parallel = moving_pos.get("decl", 0.0) - target_pos.get("decl", 0.0)
        abs_parallel = abs(delta_parallel)
        if abs_parallel <= parallel_orb:
            phase = _phase(prev_parallel, abs_parallel)
            hits.append(CoarseHit(
                kind="decl_parallel",
                when_iso=iso,
                moving=moving,
                target=target,
                delta=delta_parallel,
                applying_or_separating=phase,
            ))
        prev_parallel = abs_parallel

        delta_contra = moving_pos.get("decl", 0.0) + target_pos.get("decl", 0.0)
        abs_contra = abs(delta_contra)
        if abs_contra <= contra_orb:
            phase = _phase(prev_contra, abs_contra)
            hits.append(CoarseHit(
                kind="decl_contra",
                when_iso=iso,
                moving=moving,
                target=target,
                delta=delta_contra,
                applying_or_separating=phase,
            ))
        prev_contra = abs_contra
    return hits


def _signed_delta(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def _mirror_antiscia(lon: float) -> float:
    return (180.0 - lon) % 360.0


def _mirror_contra(lon: float) -> float:
    return (-lon) % 360.0


def detect_antiscia_contacts(
    provider: EphemerisProvider,
    ticks: Iterable[str],
    moving: str,
    target: str,
    antiscia_orb: float,
    contra_orb: float,
) -> List[CoarseHit]:
    hits: List[CoarseHit] = []
    prev_antiscia: float | None = None
    prev_contra: float | None = None
    for iso in ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        moving_pos = positions.get(moving)
        target_pos = positions.get(target)
        if not moving_pos or not target_pos:
            continue

        lon_m = moving_pos.get("lon", 0.0)
        lon_t = target_pos.get("lon", 0.0)

        mirror = _mirror_antiscia(lon_m)
        delta_antiscia = _signed_delta(mirror - lon_t)
        abs_antiscia = abs(delta_antiscia)
        if abs_antiscia <= antiscia_orb:
            phase = _phase(prev_antiscia, abs_antiscia)
            hits.append(CoarseHit(
                kind="antiscia",
                when_iso=iso,
                moving=moving,
                target=target,
                delta=delta_antiscia,
                applying_or_separating=phase,
            ))
        prev_antiscia = abs_antiscia

        mirror_contra = _mirror_contra(lon_m)
        delta_contra = _signed_delta(mirror_contra - lon_t)
        abs_contra = abs(delta_contra)
        if abs_contra <= contra_orb:
            phase = _phase(prev_contra, abs_contra)
            hits.append(CoarseHit(
                kind="contra_antiscia",
                when_iso=iso,
                moving=moving,
                target=target,
                delta=delta_contra,
                applying_or_separating=phase,
            ))
        prev_contra = abs_contra
    return hits
