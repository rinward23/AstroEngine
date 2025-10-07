"""Antiscia and contra-antiscia helpers for mirror aspect calculations."""

from __future__ import annotations

from typing import Literal

__all__ = ["antiscia", "contra_antiscia", "aspect_to_antiscia"]

MirrorKind = Literal["antiscia", "contra"]


def _normalize_longitude(lon: float) -> float:
    """Normalize ``lon`` to the [0, 360) interval."""

    return float(lon) % 360.0


def antiscia(lon: float) -> float:
    """Return the solstitial antiscia mirror of ``lon`` in degrees."""

    return (180.0 - _normalize_longitude(lon)) % 360.0


def contra_antiscia(lon: float) -> float:
    """Return the solstitial contra-antiscia mirror of ``lon`` in degrees."""

    return (360.0 - _normalize_longitude(lon)) % 360.0


def _abs_delta(a: float, b: float) -> float:
    """Return the smallest absolute separation between ``a`` and ``b`` in degrees."""

    diff = (float(a) - float(b) + 180.0) % 360.0 - 180.0
    return abs(diff)


def aspect_to_antiscia(
    body_lon: float,
    other_lon: float,
    orb: float | None,
) -> tuple[MirrorKind, float] | None:
    """Classify the relationship between two longitudes and the solstitial mirrors.

    Parameters
    ----------
    body_lon:
        Longitude of the primary body in degrees.
    other_lon:
        Longitude of the comparison body in degrees.
    orb:
        Maximum allowable separation in degrees. ``None`` disables matching.

    Returns
    -------
    Optional[Tuple[Literal["antiscia", "contra"], float]]
        When within ``orb`` degrees of either mirror, returns a tuple containing
        the mirror label (``"antiscia"`` for the solstitial reflection or
        ``"contra"`` for the contra-antiscia) and the absolute separation in
        degrees. ``None`` is returned when neither mirror falls within the
        provided orb.
    """

    if orb is None:
        return None
    try:
        allow = abs(float(orb))
    except (TypeError, ValueError):
        return None
    if allow <= 0.0:
        return None

    other = _normalize_longitude(other_lon)

    mirror = antiscia(body_lon)
    delta = _abs_delta(mirror, other)
    if delta <= allow:
        return "antiscia", delta

    contra = contra_antiscia(body_lon)
    delta_contra = _abs_delta(contra, other)
    if delta_contra <= allow:
        return "contra", delta_contra

    return None
