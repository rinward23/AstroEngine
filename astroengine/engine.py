# >>> AUTO-GEN BEGIN: AE Provider Hook v1.0
"""Provider hook helpers (non-invasive).
Call `resolve_provider(name: str)` to obtain a registered provider (default 'swiss').
Wire into scanning/refinement where positions are needed.
"""
from __future__ import annotations

from .core.engine import (
    apply_profile_if_any,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
)
from .providers import get_provider

__all__ = [
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "resolve_provider",
]


def resolve_provider(name: str | None) -> object:
    return get_provider(name or "swiss")
# >>> AUTO-GEN END: AE Provider Hook v1.0
