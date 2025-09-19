"""Core engine helpers for assembling transit events."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..modules.vca.profiles import VCA_DOMAIN_PROFILES
from .config import profile_into_ctx
from .domains import DomainResolver
from .scoring import compute_domain_factor


def _attach_domain_fields(event_obj, ctx):
    """Populate domain-related fields on ``event_obj`` using ``ctx`` metadata."""

    resolver = DomainResolver()

    sign_index = ctx.get("sign_index") if ctx else None
    planet_key = ctx.get("planet_key") if ctx else None
    house_index = ctx.get("house_index") if ctx else None

    if sign_index is None or planet_key is None:
        return

    profile_key = ctx.get("domain_profile", "vca_neutral") if ctx else "vca_neutral"
    scorer = ctx.get("domain_scorer", "weighted") if ctx else "weighted"
    temperature = float(ctx.get("domain_temperature", 8.0)) if ctx else 8.0

    resolution = resolver.resolve(sign_index=sign_index, planet_key=planet_key, house_index=house_index)
    event_obj.elements = resolution.elements
    event_obj.domains = resolution.domains
    event_obj.domain_profile = profile_key

    profile = VCA_DOMAIN_PROFILES.get(profile_key)
    if profile and hasattr(event_obj, "severity") and resolution.domains:
        factor = compute_domain_factor(
            resolution.domains,
            profile.domain_multipliers,
            method=scorer,
            temperature=temperature,
        )
        if event_obj.severity is not None:
            event_obj.severity = float(event_obj.severity) * float(factor)
        else:
            event_obj.severity = float(factor)


def maybe_attach_domain_fields(event_obj, ctx):
    """Attach domain metadata when the execution context requests it."""

    if ctx and ctx.get("emit_domains"):
        _attach_domain_fields(event_obj, ctx)
    return event_obj


def apply_profile_if_any(ctx: dict[str, Any], profile_dict: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge an optional profile into ``ctx`` and return a new dictionary."""

    if profile_dict:
        ctx = profile_into_ctx(ctx, profile_dict)
    return ctx


def get_active_aspect_angles(ctx: dict[str, Any] | None) -> Iterable[float]:
    """Return the sorted aspect angles configured in ``ctx``."""

    aspects = (ctx or {}).get("aspects", {})
    angles = []
    for key in ("major", "minor", "harmonics"):
        entries = aspects.get(key, [])
        angles.extend(entries)
    return sorted({float(angle) for angle in angles})


def get_feature_flag(ctx: dict[str, Any] | None, key: str, default: bool = False) -> bool:
    """Return the boolean feature flag stored under ``key`` in ``ctx``."""

    flags = (ctx or {}).get("flags", {})
    return bool(flags.get(key, default))


__all__ = [
    "_attach_domain_fields",
    "maybe_attach_domain_fields",
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
]
