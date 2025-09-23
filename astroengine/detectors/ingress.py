"""Compatibility wrapper exposing the legacy ``find_ingresses`` helper."""

from __future__ import annotations

from collections.abc import Sequence

from ..events import IngressEvent
from .ingresses import find_sign_ingresses

__all__ = ["find_ingresses"]


def find_ingresses(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str],
    *,
    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Return ingress events for ``bodies`` between ``start_jd`` and ``end_jd``."""

    return find_sign_ingresses(start_jd, end_jd, bodies=bodies, step_hours=step_hours)
