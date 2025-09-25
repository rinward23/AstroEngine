"""Plugin hooks for AstroEngine UX integrations."""

from __future__ import annotations

import logging
from importlib import metadata
from typing import Any

try:  # pragma: no cover - pluggy is optional at runtime
    import pluggy
except Exception:  # pragma: no cover - graceful degradation
    pluggy = None  # type: ignore

LOG = logging.getLogger(__name__)
_NAMESPACE = "astroengine"

__all__ = ["setup_cli", "hookimpl", "hookspec"]

if pluggy is not None:  # pragma: no branch
    hookspec = pluggy.HookspecMarker(_NAMESPACE)
    hookimpl = pluggy.HookimplMarker(_NAMESPACE)

    class AstroEngineSpec:
        """Hook specifications exposed to AstroEngine plugins."""

        @hookspec
        def setup_cli(self, parser: Any) -> None:
            """Augment :mod:`argparse` parsers with additional commands or options."""

    _MANAGER = pluggy.PluginManager(_NAMESPACE)
    _MANAGER.add_hookspecs(AstroEngineSpec)

    _REGISTERED_TYPES: set[type] = set()
    _BUILTINS_LOADED = False
    _ENTRYPOINTS_LOADED = False

    def _register_plugin(plugin: object, *, name: str | None = None) -> None:
        if type(plugin) in _REGISTERED_TYPES:
            return
        _MANAGER.register(plugin, name=name)
        _REGISTERED_TYPES.add(type(plugin))

    def _register_builtin_plugins() -> None:
        global _BUILTINS_LOADED
        if _BUILTINS_LOADED:
            return
        from .example import ExamplePlugin

        _register_plugin(ExamplePlugin(), name="astroengine_example_builtin")
        _BUILTINS_LOADED = True

    def _load_entrypoint_plugins(group: str = "astroengine.plugins") -> None:
        global _ENTRYPOINTS_LOADED
        if _ENTRYPOINTS_LOADED:
            return
        for entry in metadata.entry_points().select(group=group):
            try:
                plugin = entry.load()
            except Exception:  # pragma: no cover - defensive logging
                LOG.exception("Failed to load AstroEngine plugin '%s'", entry.name)
                continue
            _register_plugin(plugin, name=entry.name)
        _ENTRYPOINTS_LOADED = True

    def setup_cli(parser: Any) -> pluggy.PluginManager | None:
        """Load plugins and dispatch CLI hooks."""

        _register_builtin_plugins()
        _load_entrypoint_plugins()
        _MANAGER.hook.setup_cli(parser=parser)
        return _MANAGER

else:  # pragma: no cover - pluggy unavailable

    def setup_cli(parser: Any) -> None:
        """No-op fallback when :mod:`pluggy` is missing."""

        LOG.debug("Pluggy not available; skipping plugin hooks")
        return None

    class _Marker:
        def __call__(
            self, *args: Any, **kwargs: Any
        ) -> Any:  # pragma: no cover - debug aid
            return None

    hookimpl = hookspec = _Marker()
