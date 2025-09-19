"""Compatibility layer for :mod:`astroengine.core.engine`."""

from __future__ import annotations

from .core.engine import (
    apply_profile_if_any,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
)

__all__ = [
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
]
