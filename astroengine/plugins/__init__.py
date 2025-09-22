"""Plugin runtime and hook specifications for AstroEngine."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
import logging
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

import pluggy

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imports for static typing only
    from astroengine.exporters import LegacyTransitEvent
    from astroengine.scoring import ScoreInputs, ScoreResult


LOGGER = logging.getLogger(__name__)

PLUGIN_NAMESPACE = "astroengine"
PLUGIN_API_VERSION = "1.0"
ENTRYPOINT_GROUP = "astroengine.plugins"

hookspec = pluggy.HookspecMarker(PLUGIN_NAMESPACE)
hookimpl = pluggy.HookimplMarker(PLUGIN_NAMESPACE)


class HookSpecs:
    """Declarations of public hook specifications."""

    @hookspec
    def register_detectors(self, registry: "DetectorRegistry") -> None:
        """Register additional detector callables."""

    @hookspec
    def extend_scoring(self, registry: "ScoreExtensionRegistry") -> None:
        """Attach additional computed components to score results."""

    @hookspec
    def post_export(self, context: "ExportContext") -> None:
        """Run after an export command completes."""

    @hookspec
    def ui_panels(self) -> Iterable["UIPanelSpec"]:
        """Return lightweight UI panel descriptors for downstream apps."""


DetectorCallable = Callable[["DetectorContext"], Iterable["LegacyTransitEvent"]]
ScoreExtensionCallable = Callable[["ScoreInputs", "ScoreResult"], Mapping[str, float]]


@dataclass(frozen=True)
class DetectorSpec:
    """Metadata describing a registered detector."""

    name: str
    callback: DetectorCallable
    metadata: Mapping[str, Any] = field(default_factory=dict)


class DetectorRegistry:
    """Mutable registry of detector callables exposed to plugins."""

    def __init__(self) -> None:
        self._detectors: MutableMapping[str, DetectorSpec] = {}

    def register(
        self,
        name: str,
        callback: DetectorCallable,
        *,
        metadata: Mapping[str, Any] | None = None,
        replace: bool = False,
    ) -> None:
        if not callable(callback):  # pragma: no cover - sanity guard
            raise TypeError("detector callback must be callable")
        if name in self._detectors and not replace:
            raise ValueError(f"detector already registered: {name}")
        spec = DetectorSpec(name=name, callback=callback, metadata=dict(metadata or {}))
        self._detectors[name] = spec

    def get(self, name: str) -> DetectorSpec:
        return self._detectors[name]

    def __contains__(self, name: str) -> bool:
        return name in self._detectors

    def __iter__(self) -> Iterable[DetectorSpec]:
        return iter(self._detectors.values())

    def items(self) -> Iterable[tuple[str, DetectorSpec]]:
        return self._detectors.items()

    def names(self) -> Sequence[str]:
        return tuple(self._detectors)


@dataclass(frozen=True)
class ScoreExtensionSpec:
    """Descriptor for a computed score component supplied by plugins."""

    name: str
    callback: ScoreExtensionCallable
    namespace: str | None = None


class ScoreExtensionRegistry:
    """Collect score extension callbacks and apply them to results."""

    def __init__(self) -> None:
        self._extensions: list[ScoreExtensionSpec] = []

    def register(
        self,
        name: str,
        callback: ScoreExtensionCallable,
        *,
        namespace: str | None = None,
    ) -> None:
        if not callable(callback):  # pragma: no cover - sanity guard
            raise TypeError("score extension callback must be callable")
        self._extensions.append(
            ScoreExtensionSpec(name=name, callback=callback, namespace=namespace or name)
        )

    def iter_extensions(self) -> Iterable[ScoreExtensionSpec]:
        return tuple(self._extensions)

    def apply(self, inputs: "ScoreInputs", result: "ScoreResult") -> None:
        for spec in self._extensions:
            payload = spec.callback(inputs, result) or {}
            for key, value in payload.items():
                namespaced = f"{spec.namespace}.{key}" if spec.namespace else key
                if namespaced in result.components:
                    raise ValueError(
                        f"score component '{namespaced}' already present; plugin '{spec.name}'"
                        " attempted to overwrite an existing value"
                    )
                try:
                    result.components[namespaced] = float(value)
                except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                    raise TypeError(
                        f"score extension '{spec.name}' returned non-numeric value for '{key}'"
                    ) from exc

    def __bool__(self) -> bool:
        return bool(self._extensions)


@dataclass(frozen=True)
class ExportContext:
    """Information about a completed export run passed to plugins."""

    destinations: Mapping[str, int]
    events: Sequence[Any]
    arguments: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class UIPanelSpec:
    """Descriptor for a UI contribution provided by plugins."""

    identifier: str
    label: str
    component: str
    props: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectorContext:
    """Context supplied to plugin detectors during execution."""

    provider: Any
    provider_name: str
    start_iso: str
    end_iso: str
    ticks: Sequence[str]
    moving: str
    target: str
    options: Mapping[str, Any]
    existing_events: Sequence["LegacyTransitEvent"]


class PluginRuntime:
    """Runtime manager that loads plugins and exposes hook helpers."""

    def __init__(self, *, autoload_entrypoints: bool = True) -> None:
        self._autoload_entrypoints = autoload_entrypoints
        self._pm = pluggy.PluginManager(PLUGIN_NAMESPACE)
        self._pm.add_hookspecs(HookSpecs)
        self._entrypoints_loaded = False
        self._loaded_entrypoints: list[str] = []
        self._detectors: DetectorRegistry | None = None
        self._score_extensions: ScoreExtensionRegistry | None = None
        self._ui_panels: tuple[UIPanelSpec, ...] | None = None

    # ------------------------------------------------------------------
    # Entry point discovery
    # ------------------------------------------------------------------
    def _ensure_entrypoints(self) -> None:
        if self._autoload_entrypoints and not self._entrypoints_loaded:
            self.load_entrypoints()

    def load_entrypoints(self) -> list[str]:
        if self._entrypoints_loaded:
            return list(self._loaded_entrypoints)
        discovered: list[str] = []
        try:
            eps = metadata.entry_points()
        except Exception:  # pragma: no cover - importlib metadata guard
            eps = ()
        if hasattr(eps, "select"):
            group_eps = eps.select(group=ENTRYPOINT_GROUP)
        else:  # pragma: no cover - deprecated API shim
            group_eps = eps.get(ENTRYPOINT_GROUP, [])  # type: ignore[index]
        for ep in sorted(group_eps, key=lambda e: e.name):
            try:
                plugin = ep.load()
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Failed to load plugin '%s': %s", ep.name, exc)
                continue
            try:
                self.register_plugin(plugin, name=ep.name)
            except Exception as exc:  # pragma: no cover - compatibility guard
                LOGGER.warning("Skipping plugin '%s': %s", ep.name, exc)
                continue
            discovered.append(ep.name)
        self._entrypoints_loaded = True
        self._loaded_entrypoints = discovered
        return list(discovered)

    def loaded_entrypoints(self) -> tuple[str, ...]:
        """Return the names of entry points loaded so far."""

        self._ensure_entrypoints()
        return tuple(self._loaded_entrypoints)

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------
    def register_plugin(self, plugin: Any, *, name: str | None = None) -> None:
        self._validate_plugin_version(plugin, source=name or getattr(plugin, "__name__", "?"))
        self._pm.register(plugin, name=name)
        # Reset caches so hooks re-run on next access
        self._detectors = None
        self._score_extensions = None
        self._ui_panels = None

    # ------------------------------------------------------------------
    # Runtime accessors
    # ------------------------------------------------------------------
    def detectors(self) -> DetectorRegistry:
        self._ensure_entrypoints()
        if self._detectors is None:
            registry = DetectorRegistry()
            self._pm.hook.register_detectors(registry=registry)
            self._detectors = registry
        return self._detectors

    def score_extensions(self) -> ScoreExtensionRegistry:
        self._ensure_entrypoints()
        if self._score_extensions is None:
            registry = ScoreExtensionRegistry()
            self._pm.hook.extend_scoring(registry=registry)
            self._score_extensions = registry
        return self._score_extensions

    def collect_ui_panels(self) -> tuple[UIPanelSpec, ...]:
        self._ensure_entrypoints()
        if self._ui_panels is None:
            panels: list[UIPanelSpec] = []
            for payload in self._pm.hook.ui_panels():
                if not payload:
                    continue
                for entry in payload:
                    if isinstance(entry, UIPanelSpec):
                        panels.append(entry)
                    elif isinstance(entry, Mapping):
                        panels.append(
                            UIPanelSpec(
                                identifier=str(entry.get("identifier")),
                                label=str(entry.get("label", entry.get("identifier", ""))),
                                component=str(entry.get("component")),
                                props=dict(entry.get("props", {})),
                            )
                        )
                    else:  # pragma: no cover - defensive
                        raise TypeError(
                            "ui_panels hook must yield UIPanelSpec or mapping, got "
                            f"{type(entry)!r}"
                        )
            self._ui_panels = tuple(panels)
        return self._ui_panels

    def run_detectors(self, context: DetectorContext) -> list["LegacyTransitEvent"]:
        registry = self.detectors()
        events: list["LegacyTransitEvent"] = []
        for spec in registry:
            try:
                produced = list(spec.callback(context) or [])
            except Exception as exc:  # pragma: no cover - plugin isolation
                LOGGER.warning("detector '%s' raised an exception: %s", spec.name, exc)
                continue
            for event in produced:
                events.append(_coerce_legacy_event(event))
        return events

    def apply_score_extensions(self, inputs: "ScoreInputs", result: "ScoreResult") -> None:
        registry = self.score_extensions()
        if registry:
            registry.apply(inputs, result)

    def post_export(self, context: ExportContext) -> None:
        self._ensure_entrypoints()
        self._pm.hook.post_export(context=context)

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------
    def _validate_plugin_version(self, plugin: Any, *, source: str) -> None:
        declared = _extract_plugin_api(plugin)
        if declared is None:
            raise RuntimeError(
                f"plugin '{source}' does not declare ASTROENGINE_PLUGIN_API; expected"
                f" compatibility with {PLUGIN_API_VERSION}"
            )
        if not _is_version_compatible(declared, PLUGIN_API_VERSION):
            raise RuntimeError(
                f"plugin '{source}' targets plugin API {declared}, incompatible with"
                f" runtime {PLUGIN_API_VERSION}"
            )


def _extract_plugin_api(plugin: Any) -> str | None:
    for attr in ("ASTROENGINE_PLUGIN_API", "astroengine_plugin_api", "plugin_api_version"):
        value = getattr(plugin, attr, None)
        if value is not None:
            return str(value)
    return None


def _version_major(version: str) -> str:
    return str(version).split(".")[0]


def _is_version_compatible(declared: str, runtime: str) -> bool:
    return _version_major(declared) == _version_major(runtime)


def _coerce_legacy_event(value: Any) -> "LegacyTransitEvent":
    from astroengine.exporters import LegacyTransitEvent  # local import to avoid cycles

    if isinstance(value, LegacyTransitEvent):
        return value
    attr_fields = (
        "kind",
        "timestamp",
        "moving",
        "target",
        "orb_abs",
        "orb_allow",
        "applying_or_separating",
        "score",
    )
    if all(hasattr(value, field) for field in attr_fields):
        return LegacyTransitEvent(
            kind=getattr(value, "kind"),
            timestamp=getattr(value, "timestamp"),
            moving=getattr(value, "moving"),
            target=getattr(value, "target"),
            orb_abs=float(getattr(value, "orb_abs")),
            orb_allow=float(getattr(value, "orb_allow")),
            applying_or_separating=str(getattr(value, "applying_or_separating")),
            score=float(getattr(value, "score")),
            lon_moving=getattr(value, "lon_moving", None),
            lon_target=getattr(value, "lon_target", None),
            metadata=dict(getattr(value, "metadata", {}) or {}),
        )
    if isinstance(value, Mapping):
        required = {
            "kind",
            "timestamp",
            "moving",
            "target",
            "orb_abs",
            "orb_allow",
            "applying_or_separating",
            "score",
        }
        missing = [key for key in required if key not in value]
        if missing:
            raise TypeError(
                "mapping returned by detector is missing required keys: " + ", ".join(missing)
            )
        metadata = dict(value.get("metadata", {}))
        return LegacyTransitEvent(
            kind=value["kind"],
            timestamp=value["timestamp"],
            moving=value["moving"],
            target=value["target"],
            orb_abs=float(value["orb_abs"]),
            orb_allow=float(value["orb_allow"]),
            applying_or_separating=str(value["applying_or_separating"]),
            score=float(value["score"]),
            lon_moving=value.get("lon_moving"),
            lon_target=value.get("lon_target"),
            metadata=metadata,
        )
    raise TypeError(f"detector returned unsupported event type: {type(value)!r}")


_RUNTIME: PluginRuntime | None = None


def get_plugin_manager() -> PluginRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        runtime = PluginRuntime(autoload_entrypoints=True)
        runtime._ensure_entrypoints()
        _RUNTIME = runtime
    return _RUNTIME


def set_plugin_manager(runtime: PluginRuntime | None) -> None:
    global _RUNTIME
    _RUNTIME = runtime


def apply_score_extensions(inputs: "ScoreInputs", result: "ScoreResult") -> "ScoreResult":
    runtime = get_plugin_manager()
    runtime.apply_score_extensions(inputs, result)
    return result


__all__ = [
    "PLUGIN_API_VERSION",
    "DetectorContext",
    "DetectorRegistry",
    "DetectorSpec",
    "ExportContext",
    "PluginRuntime",
    "ScoreExtensionRegistry",
    "ScoreExtensionSpec",
    "UIPanelSpec",
    "apply_score_extensions",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "set_plugin_manager",
]
