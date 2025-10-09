"""Minimal Streamlit shim for automated testing."""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from ._runtime import ButtonWidget, MultiSelectWidget, StreamlitRuntime
from ._runtime import Widget as _Widget

__all__ = [
    "AppTestUnavailableError",
    "ButtonWidget",
    "MultiSelectWidget",
    "cache_data",
    "file_uploader",
    "datetime_input",
    "columns",
    "expander",
    "number_input",
    "plotly_chart",
    "toast",
    "radio",
    "spinner",
    "set_runtime",
    "sidebar",
    "session_state",
    "stop",
    "StreamlitStop",
    "tabs",

    "StopExecution",

]


class AppTestUnavailableError(RuntimeError):
    """Raised when the shim is used without an active runtime."""


class StopExecution(RuntimeError):
    """Raised when ``st.stop`` is invoked during a shimmed run."""


_RUNTIME: StreamlitRuntime | None = None

_WIDGETS: dict[str, dict[str, _Widget]] = {"main": {}, "sidebar": {}}
_CURRENT_CONTAINER: list[str] = ["main"]


def _current_container() -> str:
    return _CURRENT_CONTAINER[-1] if _CURRENT_CONTAINER else "main"


def _register_widget(widget: _Widget) -> _Widget:
    runtime = widget.runtime
    runtime.register(widget)
    container = _current_container()
    _WIDGETS.setdefault(container, {})[widget.label] = widget
    return widget


@contextmanager
def _container_scope(name: str) -> Iterator[None]:
    _CURRENT_CONTAINER.append(name)
    try:
        yield
    finally:
        if len(_CURRENT_CONTAINER) > 1:
            _CURRENT_CONTAINER.pop()


def _trigger_key(label: str, key: str | None = None) -> str:
    return key or f"button:{label}"


class _SessionStateProxy:
    def __getitem__(self, key: str) -> Any:
        return _require_runtime().session_state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        _require_runtime().session_state[key] = value

    def __contains__(self, key: object) -> bool:
        return key in _require_runtime().session_state

    def get(self, key: str, default: Any = None) -> Any:
        return _require_runtime().session_state.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        return _require_runtime().session_state.setdefault(key, default)

    def update(self, *args: Any, **kwargs: Any) -> None:
        _require_runtime().session_state.update(*args, **kwargs)

    def pop(self, key: str, default: Any = None) -> Any:
        return _require_runtime().session_state.pop(key, default)

    def clear(self) -> None:
        _require_runtime().session_state.clear()

    def keys(self):  # pragma: no cover - convenience passthrough
        return _require_runtime().session_state.keys()

    def items(self):  # pragma: no cover - convenience passthrough
        return _require_runtime().session_state.items()

    def values(self):  # pragma: no cover - convenience passthrough
        return _require_runtime().session_state.values()

    def __iter__(self) -> Iterator[str]:
        return iter(_require_runtime().session_state)

    def __len__(self) -> int:
        return len(_require_runtime().session_state)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - attribute access fallback
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:  # pragma: no cover - attribute access fallback
            self[name] = value


session_state = _SessionStateProxy()


class _Sidebar:
    def __enter__(self) -> _Sidebar:

        _CURRENT_CONTAINER.append("sidebar")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if len(_CURRENT_CONTAINER) > 1:
            _CURRENT_CONTAINER.pop()

        return False

    def header(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def selectbox(self, label: str, options: Sequence[Any], **kwargs: Any) -> Any:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-selectbox:{label}"

        with _container_scope("sidebar"):
            return selectbox(label, options, **kwargs)

    def multiselect(
        self, label: str, options: Sequence[Any], **kwargs: Any
    ) -> list[Any]:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-multiselect:{label}"

        with _container_scope("sidebar"):
            return multiselect(label, options, **kwargs)

    def text_input(self, label: str, **kwargs: Any) -> str:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-text:{label}"

        with _container_scope("sidebar"):
            return text_input(label, **kwargs)

    def slider(self, label: str, **kwargs: Any) -> Any:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-slider:{label}"

        with _container_scope("sidebar"):
            return slider(label, **kwargs)

    def checkbox(self, label: str, **kwargs: Any) -> bool:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-checkbox:{label}"

        with _container_scope("sidebar"):
            return checkbox(label, **kwargs)

    def button(self, label: str, **kwargs: Any) -> bool:
        key = kwargs.get("key")
        if key is None:
            kwargs["key"] = f"sidebar-button:{label}"

        with _container_scope("sidebar"):
            return button(label, **kwargs)


sidebar = _Sidebar()


def _require_runtime() -> StreamlitRuntime:
    if _RUNTIME is None:
        raise AppTestUnavailableError("Streamlit runtime not initialised")
    return _RUNTIME


def set_runtime(runtime: StreamlitRuntime) -> None:
    global _RUNTIME
    _RUNTIME = runtime

    for container in _WIDGETS.values():
        container.clear()
    _CURRENT_CONTAINER[:] = ["main"]


def cache_data(func: Callable | None = None, **_kwargs: Any) -> Callable:
    def decorator(inner: Callable) -> Callable:
        cache: dict[tuple[Any, ...], Any] = {}

        @functools.wraps(inner)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = args
            if kwargs:
                items = tuple(sorted(kwargs.items()))
                key = args + items
            if key in cache:
                return cache[key]
            result = inner(*args, **kwargs)
            cache[key] = result
            return result

        def clear() -> None:  # pragma: no cover - auxiliary helper
            cache.clear()

        wrapped.clear = clear  # type: ignore[attr-defined]
        return wrapped

    if func is not None:
        return decorator(func)
    return decorator


def set_page_config(**_kwargs: Any) -> None:
    pass


def title(*_args: Any, **_kwargs: Any) -> None:
    pass


def header(*_args: Any, **_kwargs: Any) -> None:
    pass


def subheader(*_args: Any, **_kwargs: Any) -> None:
    pass


def caption(*_args: Any, **_kwargs: Any) -> None:
    pass


def write(*_args: Any, **_kwargs: Any) -> None:
    pass


def markdown(*_args: Any, **_kwargs: Any) -> None:
    pass


def info(*_args: Any, **_kwargs: Any) -> None:
    pass


def success(*_args: Any, **_kwargs: Any) -> None:
    pass


def warning(*_args: Any, **_kwargs: Any) -> None:
    pass


def error(*_args: Any, **_kwargs: Any) -> None:
    pass


class _ToastStub:
    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def code(self, *_args: Any, **_kwargs: Any) -> None:
        pass


def toast(*_args: Any, **_kwargs: Any) -> _ToastStub:
    return _ToastStub()


def code(*_args: Any, **_kwargs: Any) -> None:
    pass


def json(*_args: Any, **_kwargs: Any) -> None:
    pass


def dataframe(*_args: Any, **_kwargs: Any) -> None:
    pass


def plotly_chart(*_args: Any, **_kwargs: Any) -> None:
    pass


def selectbox(
    label: str,
    options: Sequence[Any],
    *,
    index: int = 0,
    key: str | None = None,
    format_func: Callable[[Any], Any] | None = None,
    **_kwargs: Any,
) -> Any:
    runtime = _require_runtime()
    options_list = list(options)
    if not options_list:
        value = None
    else:
        idx = index if 0 <= index < len(options_list) else 0
        value = options_list[idx]
    if format_func is not None and value is not None:
        value = format_func(value)
    if key is not None:
        stored = runtime.session_state.get(key, value)
        runtime.session_state[key] = stored
        value = stored
    widget_key = key or f"selectbox:{label}"
    runtime.store_value(widget_key, value)

    _register_widget(
        _Widget(runtime=runtime, kind="selectbox", key=widget_key, label=label)
    )
    return value


def multiselect(
    label: str,
    options: Sequence[Any],
    *,
    default: Iterable[Any] | None = None,
    key: str | None = None,
    **_kwargs: Any,
) -> list[Any]:
    runtime = _require_runtime()
    options_list = list(options)
    if key is not None and key in runtime.session_state:
        value = list(runtime.session_state[key])
    else:
        default_values = list(default or [])
        value = [item for item in default_values if item in options_list]
        if key is not None:
            runtime.session_state[key] = list(value)
    widget_key = key or f"multiselect:{label}"
    runtime.store_value(widget_key, list(value))
    runtime.session_state.setdefault(widget_key, list(value))

    _register_widget(
        MultiSelectWidget(
            runtime=runtime,
            kind="multiselect",
            key=widget_key,
            label=label,
            options=options_list,
        )
    )
    return list(value)


def _register_text_value(
    label: str,
    value: str | None,
    *,
    key: str | None,
    kind: str,
) -> str:
    runtime = _require_runtime()
    resolved = "" if value is None else str(value)
    if key is not None:
        resolved = str(runtime.session_state.get(key, resolved))
        runtime.session_state[key] = resolved
        widget_key = key
    else:
        widget_key = f"{kind}:{label}"
    runtime.store_value(widget_key, resolved)

    _register_widget(
        _Widget(runtime=runtime, kind=kind, key=widget_key, label=label)
    )

    return resolved



def text_input(
    label: str,
    value: str | None = "",
    *,
    key: str | None = None,
    **_kwargs: Any,
) -> str:
    return _register_text_value(label, value, key=key, kind="text_input")


def text_area(
    label: str,
    value: str | None = "",
    *,
    key: str | None = None,
    **_kwargs: Any,
) -> str:
    return _register_text_value(label, value, key=key, kind="text_area")



def slider(
    label: str,
    *,
    min_value: int,
    max_value: int,
    value: int | None = None,
    step: int = 1,
    key: str | None = None,
    **_kwargs: Any,
) -> int:
    runtime = _require_runtime()
    if value is None:
        value = min_value
    value = int(value)
    if key is not None:
        stored = runtime.session_state.get(key, value)
        runtime.session_state[key] = int(stored)
        widget_key = key
        value = int(stored)
    else:
        widget_key = f"slider:{label}"
    runtime.store_value(widget_key, value)

    _register_widget(
        _Widget(runtime=runtime, kind="slider", key=widget_key, label=label)
    )

    return value


def checkbox(
    label: str,
    *,
    value: bool = False,
    key: str | None = None,
    **_kwargs: Any,
) -> bool:
    runtime = _require_runtime()
    if key is not None:
        stored = bool(runtime.session_state.get(key, value))
        runtime.session_state[key] = stored
        widget_key = key
        value = stored
    else:
        widget_key = f"checkbox:{label}"
    runtime.store_value(widget_key, value)

    _register_widget(
        _Widget(runtime=runtime, kind="checkbox", key=widget_key, label=label)
    )

    return value


class _Expander:
    def __init__(self, label: str, *, expanded: bool = False) -> None:
        self.label = label
        self.expanded = bool(expanded)

    def __enter__(self) -> _Expander:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def expander(label: str, *, expanded: bool = False) -> _Expander:
    return _Expander(label, expanded=expanded)


def button(label: str, *, key: str | None = None, **_kwargs: Any) -> bool:
    runtime = _require_runtime()
    widget_key = key or f"button:{label}"
    value = runtime.consume_click(widget_key)

    trigger_key = _trigger_key(label, key)
    if runtime.session_state.pop(trigger_key, False):
        runtime.schedule_click(widget_key)
        value = True

    runtime.store_value(widget_key, value)
    button_widget = ButtonWidget(
        runtime=runtime,
        kind="button",
        key=widget_key,
        label=label,
    )

    _register_widget(button_widget)

    return value


def download_button(*_args: Any, **_kwargs: Any) -> bool:
    return False



def radio(
    label: str,
    options: Sequence[Any],
    *,
    index: int = 0,
    key: str | None = None,
    **kwargs: Any,
) -> Any:
    return selectbox(label, options, index=index, key=key, **kwargs)


class _Expander:
    def __init__(self, label: str, *, expanded: bool = False) -> None:
        self.label = label
        self.expanded = expanded

    def __enter__(self) -> _Expander:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def expander(label: str, *, expanded: bool = False) -> _Expander:
    return _Expander(label, expanded=expanded)


def plotly_chart(*_args: Any, **_kwargs: Any) -> None:
    return None



class _Progress:
    def __init__(self) -> None:
        self.value = 0

    def progress(self, value: int, *, text: str | None = None) -> None:
        self.value = int(value)


class _Spinner:
    def __init__(self, text: str | None = None) -> None:
        self.text = text or ""

    def __enter__(self) -> _Spinner:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def spinner(text: str | None = None) -> _Spinner:
    return _Spinner(text)


class _Status:
    def __init__(self, label: str) -> None:
        self.label = label
        self.state = "running"

    def update(self, *, label: str | None = None, state: str | None = None) -> None:
        if label is not None:
            self.label = label
        if state is not None:
            self.state = state


def progress(value: int, *, text: str | None = None) -> _Progress:
    widget = _Progress()
    widget.progress(value, text=text)
    return widget


def status(label: str, *, expanded: bool = False) -> _Status:
    return _Status(label)


class _Tab:
    def __init__(self, label: str) -> None:
        self.label = label

    def __enter__(self) -> _Tab:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def tabs(labels: Sequence[str]) -> tuple[_Tab, ...]:
    return tuple(_Tab(label) for label in labels)


class _Column:
    def __init__(self, weight: float | None = None) -> None:
        self.weight = weight

    def __enter__(self) -> _Column:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def columns(
    spec: int | Sequence[int | float], *, gap: str | None = None
) -> tuple[_Column, ...]:
    if isinstance(spec, int):
        count = spec
        weights: tuple[float | None, ...] = (None,) * count
    else:
        weights = tuple(float(value) for value in spec)
        count = len(weights)

    if count < 1:
        raise ValueError("columns: at least one column required")

    return tuple(_Column(weight) for weight in weights)



def experimental_rerun() -> None:
    return None


def stop() -> None:
    raise StopExecution()
