"""Severity curves for synastry aspect hits."""

from __future__ import annotations

import math
from collections.abc import Iterable

__all__ = ["cosine_taper", "batch_cosine_taper"]


_EPSILON = 1e-9


def cosine_taper(offset: float, orb: float, gamma: float = 1.0) -> float:
    """Return cosine-tapered severity for ``offset`` within ``orb``.

    Parameters
    ----------
    offset:
        Absolute separation between the pair and the exact aspect angle in degrees.
    orb:
        Effective orb allowance for the aspect.
    gamma:
        Optional exponent to steepen (``gamma > 1``) or soften (``gamma < 1``) the taper.
    """

    orb = float(orb)
    offset = abs(float(offset))
    if orb <= _EPSILON:
        return 1.0 if offset <= _EPSILON else 0.0
    ratio = min(1.0, offset / orb)
    severity = 0.5 * (1.0 + math.cos(math.pi * ratio))
    if gamma != 1.0:
        severity = severity**float(gamma)
    return float(max(0.0, min(1.0, severity)))


def batch_cosine_taper(offsets: Iterable[float], orbs: Iterable[float], gamma: float = 1.0) -> list[float]:
    """Return severity values for corresponding ``offsets`` and ``orbs``."""

    return [cosine_taper(offset, orb, gamma=gamma) for offset, orb in zip(offsets, orbs, strict=False)]

