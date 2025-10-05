"""API routers for AstroEngine Plus services."""


from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "aspects_router",
    "charts_router",
    "clear_position_provider",
    "configure_position_provider",
    "data_router",
    "declinations_router",
    "electional_router",
    "events_router",

    "declinations_router",
    "doctor_router",

    "policies_router",
    "lots_router",
    "narrative_mix_router",
    "narrative_profiles_router",
    "notes_router",
    "policies_router",
    "profiles_router",
    "relationship_router",
    "rel_router",
    "reports_router",
    "settings_router",
    "notes_router",
    "data_router",
    "charts_router",
    "profiles_router",
    "narrative_profiles_router",
    "narrative_mix_router",
    "configure_position_provider",
    "clear_position_provider",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "aspects_router": ("aspects", "router"),
    "charts_router": ("charts", "router"),
    "clear_position_provider": ("aspects", "clear_position_provider"),
    "configure_position_provider": ("aspects", "configure_position_provider"),
    "data_router": ("data_io", "router"),
    "declinations_router": ("declinations", "router"),
    "electional_router": ("electional", "router"),
    "events_router": ("events", "router"),
    "health_router": ("health", "router"),
    "interpret_router": ("interpret", "router"),
    "lots_router": ("lots", "router"),
    "narrative_mix_router": ("narrative_mix", "router"),
    "narrative_profiles_router": ("narrative_profiles", "router"),
    "notes_router": ("notes", "router"),
    "policies_router": ("policies", "router"),
    "profiles_router": ("profiles", "router"),
    "relationship_router": ("relationship", "router"),
    "rel_router": ("rel", "router"),
    "reports_router": ("reports", "router"),
    "settings_router": ("settings", "router"),
    "transits_router": ("transits", "router"),
}

def __getattr__(name: str) -> Any:  # pragma: no cover - simple import trampoline
    if name == "aspects_router":
        from .aspects import router as aspects_router

        return aspects_router
    if name in {"configure_position_provider", "clear_position_provider"}:
        from .aspects import (
            clear_position_provider,
            configure_position_provider,
        )

        return (
            configure_position_provider
            if name == "configure_position_provider"
            else clear_position_provider
        )
    if name == "electional_router":
        from .electional import router as electional_router

        return electional_router
    if name == "events_router":
        from .events import router as events_router

        return events_router
    if name == "declinations_router":
        from .declinations import router as declinations_router

        return declinations_router
    if name == "health_router":
        from .health import router as health_router

        return health_router
    if name == "doctor_router":
        from .doctor import router as doctor_router

        return doctor_router
    if name == "interpret_router":
        from .interpret import router as interpret_router

        return interpret_router
    if name == "lots_router":
        from .lots import router as lots_router

        return lots_router
    if name == "relationship_router":
        from .relationship import router as relationship_router

        return relationship_router
    if name == "profiles_router":
        from .profiles import router as profiles_router

        return profiles_router
    if name == "narrative_profiles_router":
        from .narrative_profiles import router as narrative_profiles_router

        return narrative_profiles_router
    if name == "narrative_mix_router":
        from .narrative_mix import router as narrative_mix_router

        return narrative_mix_router
    if name == "reports_router":
        from .reports import router as reports_router

def __getattr__(name: str) -> Any:  # pragma: no cover - simple import trampoline
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise AttributeError(name) from exc

    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:  # pragma: no cover - introspection helper
    return sorted(__all__)
