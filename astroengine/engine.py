"""Core assembly helpers for AstroEngine transit events."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from .api import TransitEvent
from .domains import DomainResolver
from .profiles import VCA_DOMAIN_PROFILES

__all__ = [
    "DomainResolver",
    "VCA_DOMAIN_PROFILES",
    "build_transit_event",
    "attach_domain_fields",
]

# >>> AUTO-GEN BEGIN: Engine Domain Injection v1.0
# Instantiate once; can be swapped by callers if needed.
_domain_resolver = DomainResolver()


# Hook this inside the event construction path after sign/house/planet are known
# Pseudo-API expected context keys: sign_index, planet_key, house_index, severity, profile_key

def _attach_domain_fields(event_obj: TransitEvent, ctx: Mapping[str, Any], *, resolver: Optional[DomainResolver] = None,
                          overrides: Optional[Mapping[str, Mapping]] = None) -> None:
    resolver = resolver or _domain_resolver
    if resolver is None:
        return
    sign_index = ctx.get("sign_index")
    planet_key = ctx.get("planet_key")
    if sign_index is None or planet_key is None:
        return
    house_index = ctx.get("house_index")
    profile_key = ctx.get("domain_profile", "vca_neutral")

    res = resolver.resolve(sign_index=sign_index, planet_key=planet_key, house_index=house_index, overrides=overrides)
    event_obj.elements = res.elements
    event_obj.domains = res.domains
    event_obj.domain_profile = profile_key

    # Optional: apply domain severity multiplier to existing numeric severity if present
    prof = VCA_DOMAIN_PROFILES.get(profile_key)
    if prof and hasattr(event_obj, "severity") and event_obj.domains and event_obj.severity is not None:
        # Weight by the highest contributing domain (arg-max), then multiply
        top_domain = max(event_obj.domains.items(), key=lambda kv: kv[1])[0]
        mult = prof.domain_multipliers.get(top_domain, 1.0)
        event_obj.severity = float(event_obj.severity) * float(mult)


# >>> AUTO-GEN END: Engine Domain Injection v1.0


def attach_domain_fields(event_obj: TransitEvent, ctx: Mapping[str, Any], *, resolver: Optional[DomainResolver] = None,
                         overrides: Optional[Mapping[str, Mapping]] = None) -> None:
    """Public helper that mirrors :func:`_attach_domain_fields` but exposes dependency injection."""

    _attach_domain_fields(event_obj, ctx, resolver=resolver, overrides=overrides)


def build_transit_event(
    ctx: Mapping[str, Any] | MutableMapping[str, Any],
    *,
    emit_domains: bool = False,
    resolver: Optional[DomainResolver] = None,
    overrides: Optional[Mapping[str, Mapping]] = None,
    base_event: Optional[TransitEvent] = None,
) -> TransitEvent:
    """Construct a :class:`TransitEvent` from a context mapping.

    Parameters
    ----------
    ctx:
        Mapping containing event metadata such as sign index, planet key, and
        severity.  Callers are responsible for populating these values from
        trusted runtime data sources.
    emit_domains:
        When ``True`` the function resolves the element/domain annotations and
        applies the domain severity multiplier defined by the chosen profile.
    resolver:
        Optional resolver instance to use in place of the module singleton.
    overrides:
        Optional weights override payload forwarded to :class:`DomainResolver`.
    base_event:
        Optional pre-constructed :class:`TransitEvent` instance to decorate.
    """

    event = base_event or TransitEvent()
    if "severity" in ctx:
        try:
            event.severity = float(ctx["severity"]) if ctx["severity"] is not None else None
        except (TypeError, ValueError):
            event.severity = None
    if emit_domains:
        ctx_with_profile = dict(ctx)
        if "domain_profile" not in ctx_with_profile:
            ctx_with_profile["domain_profile"] = "vca_neutral"
        _attach_domain_fields(event, ctx_with_profile, resolver=resolver, overrides=overrides or ctx.get("domain_overrides"))
    return event
