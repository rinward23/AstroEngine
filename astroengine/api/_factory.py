"""Shared FastAPI application factory utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from fastapi import FastAPI
from fastapi.routing import APIRouter
from starlette.responses import Response

MiddlewareInstaller = Callable[[FastAPI], None]
Observer = Callable[[FastAPI], None]
StartupHook = Callable[[FastAPI], None]
OnCreateHook = Callable[[FastAPI], None]


@dataclass(frozen=True)
class RouterSpec:
    """Metadata describing how an :class:`APIRouter` should be mounted."""

    router: APIRouter
    prefix: str | None = None
    tags: Sequence[str] | None = None

    def install(self, app: FastAPI) -> None:
        """Register ``router`` on ``app`` respecting optional metadata."""

        kwargs: MutableMapping[str, Any] = {}
        if self.prefix:
            kwargs["prefix"] = self.prefix
        if self.tags is not None:
            kwargs["tags"] = list(self.tags)
        app.include_router(self.router, **kwargs)


@dataclass(frozen=True)
class AppFactoryConfig:
    """Configuration bundle describing how to assemble a FastAPI app."""

    title: str
    version: str | None = None
    default_response_class: type[Response] | None = None
    openapi_tags: Sequence[Mapping[str, Any]] | None = None
    state: Mapping[str, Any] | None = None
    middlewares: Sequence[MiddlewareInstaller] = field(default_factory=tuple)
    observability: Sequence[Observer] = field(default_factory=tuple)
    routers: Sequence[RouterSpec] = field(default_factory=tuple)
    startup_hooks: Sequence[StartupHook] = field(default_factory=tuple)
    on_create: Sequence[OnCreateHook] = field(default_factory=tuple)


def create_app(config: AppFactoryConfig) -> FastAPI:
    """Instantiate a FastAPI application according to ``config``."""

    app = FastAPI(
        title=config.title,
        version=config.version,
        default_response_class=config.default_response_class,
        openapi_tags=list(config.openapi_tags) if config.openapi_tags else None,
    )

    if config.state:
        for key, value in config.state.items():
            setattr(app.state, key, value)

    for installer in config.middlewares:
        installer(app)

    for observer in config.observability:
        observer(app)

    for spec in config.routers:
        spec.install(app)

    for hook in config.startup_hooks:
        hook(app)

    for callback in config.on_create:
        callback(app)

    return app


__all__ = ["AppFactoryConfig", "RouterSpec", "create_app"]

