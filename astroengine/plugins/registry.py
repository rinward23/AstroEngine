"""Lightweight registries for user-supplied aspect and lot plugins."""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, MutableMapping


LOGGER = logging.getLogger(__name__)

_USER_PLUGIN_NAMESPACE = "astroengine_user_plugins"


def _ensure_namespace_package() -> None:
    if _USER_PLUGIN_NAMESPACE in sys.modules:
        return
    pkg = ModuleType(_USER_PLUGIN_NAMESPACE)
    pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules[_USER_PLUGIN_NAMESPACE] = pkg


def _slugify(value: str) -> str:
    filtered = [ch if ch.isalnum() else "_" for ch in value.strip().lower()]
    collapsed = "".join(filtered)
    parts = [chunk for chunk in collapsed.split("_") if chunk]
    return "_".join(parts)


def _normalize_key(name: str, origin: str | None) -> str:
    base = _slugify(name)
    if origin:
        origin_slug = _slugify(origin.replace(".", "_"))
        if origin_slug:
            return f"{origin_slug}__{base}"
    return base


def _infer_origin(callable_obj: Callable[..., Any] | None) -> tuple[str | None, str | None]:
    module_name = getattr(callable_obj, "__module__", None) if callable_obj else None
    module_file: str | None = None
    if module_name:
        module = sys.modules.get(module_name)
        module_file = getattr(module, "__file__", None)
    if module_name is None:
        try:
            frame = inspect.stack()[2].frame
        except IndexError:  # pragma: no cover - defensive guard
            frame = inspect.currentframe()
        while frame:
            module_name = frame.f_globals.get("__name__")
            module_file = frame.f_globals.get("__file__")
            if module_name and not module_name.startswith("astroengine.plugins.registry"):
                break
            frame = frame.f_back  # type: ignore[assignment]
    return module_name, module_file


def _default_plugin_dir() -> Path:
    override = os.environ.get("ASTROENGINE_PLUGIN_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(
            os.environ.get(
                "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
            )
        )
        return base / "AstroEngine" / "plugins"
    base = Path(os.environ.get("ASTROENGINE_HOME", str(Path.home() / ".astroengine")))
    return base / "plugins"


PLUGIN_DIRECTORY = _default_plugin_dir()


@dataclass(frozen=True)
class AspectPluginSpec:
    """Descriptor for a registered custom aspect."""

    key: str
    name: str
    runtime_name: str
    angle: float
    origin: str | None
    path: str | None
    replace: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def ui_label(self) -> str:
        angle = f"{float(self.angle):g}°"
        return f"{self.name} ({angle})"


@dataclass(frozen=True)
class LotPluginSpec:
    """Descriptor for a registered custom Arabic Lot."""

    key: str
    name: str
    day_formula: str
    night_formula: str
    description: str
    origin: str | None
    path: str | None
    replace: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)


class AspectRegistry:
    """Mutable registry capturing custom aspect definitions."""

    def __init__(self) -> None:
        self._items: MutableMapping[str, AspectPluginSpec] = {}
        self._applied: set[str] = set()
        self._original: dict[str, float] = {}

    def register(
        self,
        name: str,
        angle: float,
        *,
        origin: str | None,
        path: str | None,
        replace: bool,
        metadata: Mapping[str, Any] | None = None,
    ) -> AspectPluginSpec:
        normalized = name.strip()
        if not normalized:
            raise ValueError("aspect name cannot be empty")
        key = _normalize_key(normalized, origin)
        if not replace and key in self._items:
            raise ValueError(f"aspect already registered: {name}")
        from astroengine.core.aspects_plus import harmonics as base_module

        builtin_names = {k.lower() for k in base_module.BASE_ASPECTS.keys()}
        if not replace and normalized.lower() in builtin_names:
            raise ValueError(
                f"aspect '{name}' already exists; set replace=True to override"
            )
        spec = AspectPluginSpec(
            key=key,
            name=normalized,
            runtime_name=normalized.lower(),
            angle=float(angle),
            origin=origin,
            path=str(path) if path else None,
            replace=replace,
            metadata=dict(metadata or {}),
        )
        if not replace:
            for existing in self._items.values():
                if existing.runtime_name == spec.runtime_name:
                    raise ValueError(
                        f"aspect '{name}' already provided by another plugin"
                    )
        self._items[key] = spec
        return spec

    def iter_all(self) -> tuple[AspectPluginSpec, ...]:
        return tuple(
            sorted(self._items.values(), key=lambda spec: spec.name.lower())
        )

    def iter_enabled(
        self, toggles: Mapping[str, bool] | None = None
    ) -> tuple[AspectPluginSpec, ...]:
        toggles = toggles or {}
        active: list[AspectPluginSpec] = []
        for spec in self.iter_all():
            enabled = toggles.get(spec.key)
            if enabled is None:
                enabled = toggles.get(spec.name, True)
            if enabled is False:
                continue
            active.append(spec)
        return tuple(active)

    def apply(self, toggles: Mapping[str, bool] | None = None) -> tuple[AspectPluginSpec, ...]:
        from astroengine.core.aspects_plus import harmonics as base_module

        # Restore any prior overrides or removals.
        for name in list(self._applied):
            if name in self._original:
                base_module.BASE_ASPECTS[name] = self._original.pop(name)
            else:
                base_module.BASE_ASPECTS.pop(name, None)
        self._applied.clear()

        applied: list[AspectPluginSpec] = []
        for spec in self.iter_enabled(toggles):
            target_name = spec.runtime_name
            if target_name in base_module.BASE_ASPECTS and target_name not in self._original:
                self._original[target_name] = float(base_module.BASE_ASPECTS[target_name])
            base_module.BASE_ASPECTS[target_name] = float(spec.angle)
            self._applied.add(target_name)
            applied.append(spec)
        return tuple(applied)


class LotRegistry:
    """Mutable registry capturing custom Arabic Lot definitions."""

    def __init__(self) -> None:
        self._items: MutableMapping[str, LotPluginSpec] = {}
        self._applied: set[str] = set()
        self._original: dict[str, Any] = {}

    def register(
        self,
        name: str,
        day_formula: str,
        night_formula: str,
        *,
        origin: str | None,
        path: str | None,
        replace: bool,
        description: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LotPluginSpec:
        normalized = name.strip()
        if not normalized:
            raise ValueError("lot name cannot be empty")
        key = _normalize_key(normalized, origin)
        if not replace and key in self._items:
            raise ValueError(f"lot already registered: {name}")
        from core.lots_plus import catalog as lots_catalog

        builtin_names = {k.lower() for k in lots_catalog.REGISTRY.keys()}
        if not replace and normalized.lower() in builtin_names:
            raise ValueError(
                f"lot '{name}' already exists; set replace=True to override"
            )
        spec = LotPluginSpec(
            key=key,
            name=normalized,
            day_formula=str(day_formula),
            night_formula=str(night_formula),
            description=str(description or ""),
            origin=origin,
            path=str(path) if path else None,
            replace=replace,
            metadata=dict(metadata or {}),
        )
        if not replace:
            for existing in self._items.values():
                if existing.name.lower() == spec.name.lower():
                    raise ValueError(
                        f"lot '{name}' already provided by another plugin"
                    )
        self._items[key] = spec
        return spec

    def iter_all(self) -> tuple[LotPluginSpec, ...]:
        return tuple(sorted(self._items.values(), key=lambda spec: spec.name.lower()))

    def iter_enabled(
        self, toggles: Mapping[str, bool] | None = None
    ) -> tuple[LotPluginSpec, ...]:
        toggles = toggles or {}
        active: list[LotPluginSpec] = []
        for spec in self.iter_all():
            enabled = toggles.get(spec.key)
            if enabled is None:
                enabled = toggles.get(spec.name, True)
            if enabled is False:
                continue
            active.append(spec)
        return tuple(active)

    def apply(self, toggles: Mapping[str, bool] | None = None) -> tuple[LotPluginSpec, ...]:
        from core.lots_plus import catalog as lots_catalog

        for name in list(self._applied):
            if name in self._original:
                lots_catalog.REGISTRY[name] = self._original.pop(name)
            else:
                lots_catalog.REGISTRY.pop(name, None)
        self._applied.clear()

        applied: list[LotPluginSpec] = []
        for spec in self.iter_enabled(toggles):
            if spec.name in lots_catalog.REGISTRY and spec.name not in self._original:
                self._original[spec.name] = lots_catalog.REGISTRY[spec.name]
            lots_catalog.REGISTRY[spec.name] = lots_catalog.LotDef(
                name=spec.name,
                day=spec.day_formula,
                night=spec.night_formula,
                description=spec.description or spec.metadata.get("description", ""),
            )
            self._applied.add(spec.name)
            applied.append(spec)
        return tuple(applied)


ASPECT_REGISTRY = AspectRegistry()
LOT_REGISTRY = LotRegistry()

_USER_PLUGINS_IMPORTED = False
_USER_PLUGIN_MODULES: list[str] = []


def load_user_plugins(force: bool = False) -> tuple[str, ...]:
    """Import ``.py`` files under the user plugin directory."""

    global _USER_PLUGINS_IMPORTED
    if not force and _USER_PLUGINS_IMPORTED:
        return tuple(_USER_PLUGIN_MODULES)

    _ensure_namespace_package()
    loaded: list[str] = []
    plugin_root = PLUGIN_DIRECTORY
    if not plugin_root.exists():
        _USER_PLUGINS_IMPORTED = True
        _USER_PLUGIN_MODULES[:] = []
        return tuple(loaded)

    for path in sorted(plugin_root.glob("*.py")):
        module_name = f"{_USER_PLUGIN_NAMESPACE}.{path.stem}"
        if not force and module_name in sys.modules:
            loaded.append(module_name)
            continue
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"unable to load spec for {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            loaded.append(module_name)
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.warning("Failed to load plugin file %s: %s", path, exc)
            sys.modules.pop(module_name, None)
            continue
    _USER_PLUGINS_IMPORTED = True
    _USER_PLUGIN_MODULES[:] = loaded
    return tuple(loaded)


def ensure_user_plugins_loaded() -> tuple[str, ...]:
    if not _USER_PLUGINS_IMPORTED:
        return load_user_plugins()
    return tuple(_USER_PLUGIN_MODULES)


def register_aspect(name: str, angle: float, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator registering a custom aspect angle supplied by a plugin."""

    replace = bool(metadata.pop("replace", False))

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        origin, module_path = _infer_origin(func)
        ASPECT_REGISTRY.register(
            name=name,
            angle=angle,
            origin=origin,
            path=module_path,
            replace=replace,
            metadata=metadata,
        )
        return func

    return decorator


def register_lot(
    name: str,
    day_formula: str,
    night_formula: str,
    **metadata: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator registering a custom Arabic Lot formula supplied by a plugin."""

    replace = bool(metadata.pop("replace", False))
    description = metadata.pop("description", None)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        origin, module_path = _infer_origin(func)
        LOT_REGISTRY.register(
            name=name,
            day_formula=day_formula,
            night_formula=night_formula,
            origin=origin,
            path=module_path,
            replace=replace,
            description=description,
            metadata=metadata,
        )
        return func

    return decorator


def iter_aspect_plugins() -> tuple[AspectPluginSpec, ...]:
    ensure_user_plugins_loaded()
    return ASPECT_REGISTRY.iter_all()


def iter_lot_plugins() -> tuple[LotPluginSpec, ...]:
    ensure_user_plugins_loaded()
    return LOT_REGISTRY.iter_all()


def apply_plugin_settings(settings: Any | None = None) -> dict[str, tuple[Any, ...]]:
    """Apply configuration toggles to plugin-registered aspects and lots."""

    ensure_user_plugins_loaded()
    aspect_toggles: Mapping[str, bool] | None = None
    lot_toggles: Mapping[str, bool] | None = None

    if settings is not None:
        plugin_cfg = getattr(settings, "plugins", None)
        if plugin_cfg is not None:
            aspect_toggles = getattr(plugin_cfg, "aspects", None)
            lot_toggles = getattr(plugin_cfg, "lots", None)

    applied_aspects = ASPECT_REGISTRY.apply(aspect_toggles)
    applied_lots = LOT_REGISTRY.apply(lot_toggles)
    return {"aspects": applied_aspects, "lots": applied_lots}


__all__ = [
    "ASPECT_REGISTRY",
    "AspectPluginSpec",
    "LotPluginSpec",
    "LOT_REGISTRY",
    "PLUGIN_DIRECTORY",
    "apply_plugin_settings",
    "ensure_user_plugins_loaded",
    "iter_aspect_plugins",
    "iter_lot_plugins",
    "load_user_plugins",
    "register_aspect",
    "register_lot",
]

