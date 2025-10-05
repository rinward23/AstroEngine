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
    "health_router",
    "interpret_router",
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
    "transits_router",
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
