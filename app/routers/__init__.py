"""API routers for AstroEngine Plus services."""


from __future__ import annotations

from typing import Any

__all__ = [
    "aspects_router",
    "electional_router",
    "events_router",

    "policies_router",
    "lots_router",
    "relationship_router",
    "interpret_router",
    "reports_router",
    "health_router",
    "configure_position_provider",
    "clear_position_provider",
]


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
    if name == "health_router":
        from .health import router as health_router

        return health_router
    if name == "interpret_router":
        from .interpret import router as interpret_router

        return interpret_router
    if name == "lots_router":
        from .lots import router as lots_router

        return lots_router
    if name == "relationship_router":
        from .relationship import router as relationship_router

        return relationship_router
    if name == "reports_router":
        from .reports import router as reports_router

        return reports_router
    if name == "policies_router":
        from .policies import router as policies_router

        return policies_router
    if name == "configure_position_provider":
        from .aspects import configure_position_provider as _configure

        return _configure
    if name == "clear_position_provider":
        from .aspects import clear_position_provider as _clear

        return _clear
    if name == "rel_router":
        from .rel import router as rel_router

        return rel_router
    if name == "transits_router":
        from .transits import router as transits_router

        return transits_router
    if name == "configure_position_provider":
        from .aspects import configure_position_provider

        return configure_position_provider
    if name == "clear_position_provider":
        from .aspects import clear_position_provider

        return clear_position_provider
    raise AttributeError(name)


def __dir__() -> list[str]:  # pragma: no cover - introspection helper
    return sorted(__all__)
