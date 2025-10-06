"""Compatibility wrappers for the legacy ``astroengine.scanner`` module."""

from __future__ import annotations

from collections.abc import Iterable

from ..detectors import (
    CoarseHit,
)
from ..detectors import (
    detect_antiscia_contacts as _detect_antiscia_contacts,
)
from ..detectors import (
    detect_decl_contacts as _detect_decl_contacts,
)

__all__ = [
    "CoarseHit",
    "detect_antiscia_contacts",
    "detect_decl_contacts",
]


def detect_decl_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_parallel: float = 0.5,
    orb_deg_contra: float = 0.5,
) -> list[CoarseHit]:
    """Proxy to :func:`astroengine.detectors.detect_decl_contacts`."""

    return _detect_decl_contacts(
        provider,
        iso_ticks,
        moving,
        target,
        orb_deg_parallel,
        orb_deg_contra,
    )


def detect_antiscia_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_antiscia: float = 2.0,
    orb_deg_contra: float = 2.0,
    *,
    axis: str | None = None,
) -> list[CoarseHit]:
    """Proxy to :func:`astroengine.detectors.detect_antiscia_contacts`."""

    return _detect_antiscia_contacts(
        provider,
        iso_ticks,
        moving,
        target,
        orb_deg_antiscia,
        orb_deg_contra,
        axis=axis,
    )
