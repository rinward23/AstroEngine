"""Registry and built-in renderers for the Streamlit portal panes."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import EntryPoint, PackageNotFoundError, entry_points
from pathlib import Path
from typing import Any, Sequence

import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is an optional dependency.
    yaml = None  # type: ignore[assignment]


@dataclass(frozen=True)
class PaneSpec:
    """Description of a dashboard pane."""

    key: str
    label: str
    category: str
    renderer: Callable[[DeltaGenerator], None]


_REGISTRY: dict[str, PaneSpec] = {}
_DEFAULT_ENTRYPOINT_GROUP = "astroengine.ui.streamlit.panes"
_DEFAULT_CONFIG_FILENAMES = ("dashboard_panes.yaml", "dashboard_panes.yml", "dashboard_panes.json")
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROFILES_DIR = _REPO_ROOT / "profiles"


def register_pane(
    key: str,
    label: str,
    category: str,
    renderer: Callable[[DeltaGenerator], None] | str,
    *,
    replace: bool = False,
) -> PaneSpec:
    """Register a pane so it is discoverable by the portal."""

    resolved = _resolve_renderer(renderer)
    spec = PaneSpec(key=key, label=label, category=category, renderer=resolved)
    if not replace and key in _REGISTRY:
        raise ValueError(f"Pane '{key}' is already registered")
    _REGISTRY[key] = spec
    return spec


def load_registered_panes(
    config_path: str | Path | None = None,
    *,
    entry_point_group: str = _DEFAULT_ENTRYPOINT_GROUP,
) -> dict[str, PaneSpec]:
    """Return the registered panes augmented by configuration files and plugins."""

    panes: dict[str, PaneSpec] = dict(_REGISTRY)

    config = _resolve_config_path(config_path)
    if config:
        for record in _load_config_records(config):
            spec = _coerce_spec(record)
            panes[spec.key] = spec

    for spec in _load_entry_point_specs(entry_point_group):
        panes[spec.key] = spec

    return panes


def _resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path:
        path = Path(config_path)
        return path if path.exists() else None

    for candidate in _DEFAULT_CONFIG_FILENAMES:
        path = _PROFILES_DIR / candidate
        if path.exists():
            return path
    return None


def _load_config_records(config_path: Path) -> Sequence[dict[str, Any]]:
    if config_path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise ModuleNotFoundError(
                "PyYAML is required to parse dashboard pane configuration files"
            )
        loaded = yaml.safe_load(config_path.read_text())
    else:
        loaded = json.loads(config_path.read_text())

    if loaded is None:
        return []
    if isinstance(loaded, dict):
        loaded = loaded.get("panes", loaded)
    if not isinstance(loaded, Iterable):
        raise TypeError(
            f"Unexpected format in {config_path}: expected a list of pane definitions"
        )

    records: list[dict[str, Any]] = []
    for item in loaded:
        if not isinstance(item, dict):
            raise TypeError(
                f"Pane configuration entries must be mappings, received {type(item)!r}"
            )
        records.append(item)
    return records


def _resolve_renderer(renderer: Callable[[DeltaGenerator], None] | str) -> Callable[[DeltaGenerator], None]:
    if callable(renderer):
        return renderer
    if not isinstance(renderer, str):
        raise TypeError(
            "Pane renderer must be a callable or an import path in the form 'module:function'"
        )
    if ":" in renderer:
        module_path, attr = renderer.split(":", 1)
    else:
        module_path, attr = renderer.rsplit(".", 1)
    module = import_module(module_path)
    resolved = getattr(module, attr)
    if not callable(resolved):
        raise TypeError(f"Resolved renderer '{renderer}' is not callable")
    return resolved


def _coerce_spec(value: dict[str, Any] | PaneSpec) -> PaneSpec:
    if isinstance(value, PaneSpec):
        return value
    try:
        key = value["id"] if "id" in value else value["key"]
        label = value["label"]
        category = value["category"]
        renderer = value["renderer"]
    except KeyError as exc:
        raise KeyError(f"Missing required pane field: {exc.args[0]}") from exc
    return PaneSpec(
        key=str(key),
        label=str(label),
        category=str(category),
        renderer=_resolve_renderer(renderer),
    )


def _load_entry_point_specs(group: str) -> list[PaneSpec]:
    try:
        eps = entry_points()
    except PackageNotFoundError:
        return []

    if hasattr(eps, "select"):
        candidates: Iterable[EntryPoint] = eps.select(group=group)
    else:  # pragma: no cover - compatibility branch for older importlib.metadata.
        candidates = [ep for ep in eps if getattr(ep, "group", None) == group]

    specs: list[PaneSpec] = []
    for entry in candidates:
        try:
            loaded = entry.load()
        except Exception as exc:  # pragma: no cover - defensive logging path.
            st.warning(f"Failed to load pane entry point {entry.name}: {exc}")
            continue
        for spec in _iter_loaded_specs(loaded):
            specs.append(spec)
    return specs


def _iter_loaded_specs(loaded: Any) -> Iterable[PaneSpec]:
    if isinstance(loaded, PaneSpec):
        yield loaded
    elif isinstance(loaded, dict):
        yield _coerce_spec(loaded)
    elif isinstance(loaded, Iterable) and not isinstance(loaded, (str, bytes)):
        for item in loaded:
            if isinstance(item, PaneSpec):
                yield item
            elif isinstance(item, dict):
                yield _coerce_spec(item)
            else:
                raise TypeError(
                    "Pane entry points must provide PaneSpec objects or dictionaries"
                )
    elif callable(loaded):
        result = loaded()
        yield from _iter_loaded_specs(result)
    else:
        raise TypeError(
            "Unsupported pane entry point payload; expected PaneSpec, dict, list, or callable"
        )


def _api_base() -> str:
    return os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/")


def _render_chart(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Chart Wheel**")
    url = f"{_api_base()}/v1/plots/wheel"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            target.image(r.content, caption="Current Chart")
        else:
            target.info("Chart image endpoint not available yet. Add /v1/plots/wheel to the API to enable.")
    except Exception:
        target.info("Chart endpoint unreachable.")


def _render_aspects(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Aspect Grid**")
    url = f"{_api_base()}/v1/plots/aspects"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            target.image(r.content, caption="Aspect Grid")
        else:
            target.info("Aspect grid not available yet. Add /v1/plots/aspects.")
    except Exception:
        target.info("Aspect endpoint unreachable.")


def _render_timeline(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Timeline**")
    url = f"{_api_base()}/v1/timeline?from=now-30d&to=now+30d"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            data = r.json()
            target.json(data[:25] if isinstance(data, list) else data)
        else:
            target.info("Timeline endpoint not ready. See Task 7/10.")
    except Exception:
        target.info("Timeline endpoint unreachable.")


def _render_map(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Astrocartography Map**")
    try:
        import pydeck as pdk

        url = f"{_api_base()}/v1/astrocartography"
        r = requests.get(url, timeout=5)
        if r.ok:
            geo = r.json()
            layer = pdk.Layer("GeoJsonLayer", geo, pickable=True)
            view_state = pdk.ViewState(latitude=0, longitude=0, zoom=0.8)
            target.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
        else:
            target.info("Map endpoint not ready. See Task 12.")
    except Exception:
        target.info("pydeck not installed or map endpoint unreachable.")


def _render_custom(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Custom Panel**")
    target.caption("Bring your own graphic here — embed images, tables, or KPIs.")
    target.write("")


def _render_health(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Service Health**")
    url = f"{_api_base()}/healthz"
    try:
        r = requests.get(url, timeout=3)
        target.markdown(f"`GET {url}` → **{r.status_code}**")
        content_type = r.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            target.json(r.json())
        else:
            target.code(r.text[:2000])
    except Exception as exc:
        target.warning(f"Health endpoint unreachable: {exc}")


def _render_settings_snapshot(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Configuration Snapshot**")
    url = f"{_api_base()}/v1/settings"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            target.json(r.json())
        else:
            target.info("Settings endpoint responded without data. Ensure /v1/settings is implemented.")
    except Exception as exc:
        target.warning(f"Settings endpoint unreachable: {exc}")


def _render_metrics(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Prometheus Metrics**")
    url = f"{_api_base()}/metrics"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            target.code(r.text[:4000] + ("\n…" if len(r.text) > 4000 else ""), language="text")
        else:
            target.info("Metrics endpoint responded without data. Ensure Prometheus middleware is enabled.")
    except Exception as exc:
        target.warning(f"Metrics endpoint unreachable: {exc}")


register_pane("chart_wheel", "Chart Wheel", "Charts", _render_chart)
register_pane("aspect_grid", "Aspect Grid", "Charts", _render_aspects)
register_pane("timeline", "Event Timeline", "Temporal", _render_timeline)
register_pane("astro_map", "Astrocartography Map", "Geospatial", _render_map)
register_pane("custom_panel", "Custom Panel", "Custom", _render_custom)
register_pane("api_health", "API Health", "Diagnostics", _render_health)
register_pane("api_settings", "Configuration Snapshot", "Diagnostics", _render_settings_snapshot)
register_pane("api_metrics", "Prometheus Metrics", "Diagnostics", _render_metrics)

