"""Core runtime helpers for assembling transit events."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from .api import TransitEvent
from .scoring import compute_domain_factor  # ENSURE-LINE


# >>> AUTO-GEN BEGIN: Engine Domain Scoring Hook v1.1


def _attach_domain_fields(event_obj: TransitEvent, ctx: Mapping[str, Any]) -> None:
    from .domains import DomainResolver
    from .profiles import VCA_DOMAIN_PROFILES

    resolver = DomainResolver()

    sign_index = ctx.get("sign_index")
    planet_key = ctx.get("planet_key")
    house_index = ctx.get("house_index")

    if sign_index is None or planet_key is None:
        return

    profile_key = ctx.get("domain_profile", "vca_neutral")
    scorer = ctx.get("domain_scorer", "weighted")
    temperature = float(ctx.get("domain_temperature", 8.0))

    result = resolver.resolve(
        sign_index=int(sign_index),
        planet_key=str(planet_key),
        house_index=int(house_index) if house_index is not None else None,
    )
    event_obj.elements = result.elements
    event_obj.domains = result.domains
    event_obj.domain_profile = profile_key

    profile = VCA_DOMAIN_PROFILES.get(profile_key)
    if profile and event_obj.domains:
        factor = compute_domain_factor(
            event_obj.domains,
            profile.domain_multipliers,
            method=scorer,
            temperature=temperature,
        )
        if event_obj.severity is not None:
            event_obj.severity = float(event_obj.severity) * float(factor)


# >>> AUTO-GEN END: Engine Domain Scoring Hook v1.1


def assemble_transit_event(ctx: Mapping[str, Any]) -> TransitEvent:
    """Create a :class:`TransitEvent` from the provided context mapping."""

    event = TransitEvent()
    severity = ctx.get("severity")
    if severity is not None:
        event.severity = float(severity)

    if ctx.get("emit_domains"):
        _attach_domain_fields(event, ctx)
    return event


def event_to_mapping(event: TransitEvent) -> MutableMapping[str, Any]:
    """Return a shallow mapping view of the event for serialization."""

    return dict(event.__dict__)


__all__ = ["assemble_transit_event", "event_to_mapping", "_attach_domain_fields"]

