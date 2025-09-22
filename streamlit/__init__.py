"""Lightweight Streamlit stub used for automated tests.

The real Streamlit package is large and not available in the execution
environment for unit tests.  This stub implements enough of the API for the
`apps/streamlit_transit_scanner.py` script to run deterministically.  The goal
is not to render a UI but to provide predictable hooks that record widget
configuration and persist ``session_state`` between runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

session_state: Dict[str, Any] = {}

_WIDGETS: Dict[str, Dict[str, "_Widget"]] = {"main": {}, "sidebar": {}}
_CURRENT_CONTAINER: List[str] = ["main"]


def _container_name() -> str:
    return _CURRENT_CONTAINER[-1]


@dataclass
class _Widget:
    kind: str
    label: str
    options: Sequence[Any] | None = None
    value: Any = None

    def __iter__(self):  # pragma: no cover - compatibility
        if isinstance(self.value, Iterable) and not isinstance(self.value, (str, bytes)):
            return iter(self.value)
        return iter([self.value])


class _Context:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        _CURRENT_CONTAINER.append(self.name)
        return self

    def __exit__(self, exc_type, exc, tb):
        _CURRENT_CONTAINER.pop()
        return False

    # UI helpers simply record that the call occurred.
    def header(self, _label: str, **_kwargs: Any) -> None:
        pass

    def caption(self, _text: str, **_kwargs: Any) -> None:
        pass

    def write(self, _text: Any = "", **_kwargs: Any) -> None:
        pass

    def subheader(self, _label: str, **_kwargs: Any) -> None:
        pass

    def markdown(self, _text: str, **_kwargs: Any) -> None:
        pass

    def json(self, _obj: Any, **_kwargs: Any) -> None:
        pass

    def code(self, _code: str, **_kwargs: Any) -> None:
        pass

    def dataframe(self, _df: Any, **_kwargs: Any) -> None:
        pass

    def info(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def warning(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def error(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def success(self, _msg: str, **_kwargs: Any) -> None:
        pass


sidebar = _Context("sidebar")


def _record_widget(widget: _Widget) -> _Widget:
    _WIDGETS[_container_name()][widget.label] = widget
    return widget


def cache_data(**_kwargs: Any):  # pragma: no cover - simple passthrough
    def decorator(func):
        cache: Dict[Tuple[Any, ...], Any] = {}

        def wrapped(*args: Any, **kwargs: Any):
            key = args + tuple(sorted(kwargs.items()))
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result

        wrapped.cache = cache  # type: ignore[attr-defined]
        return wrapped

    return decorator


def set_page_config(**_kwargs: Any) -> None:
    pass


def title(_text: str) -> None:
    pass


def header(_text: str) -> None:
    pass


def subheader(_text: str) -> None:
    pass


def caption(_text: str) -> None:
    pass


def write(_text: Any = "", **_kwargs: Any) -> None:
    pass


def markdown(_text: str, **_kwargs: Any) -> None:
    pass


def info(_text: str, **_kwargs: Any) -> None:
    pass


def warning(_text: str, **_kwargs: Any) -> None:
    pass


def error(_text: str, **_kwargs: Any) -> None:
    pass


def success(_text: str, **_kwargs: Any) -> None:
    pass


def json(_obj: Any, **_kwargs: Any) -> None:
    pass


def dataframe(_df: Any, **_kwargs: Any) -> None:
    pass


def code(_text: str, **_kwargs: Any) -> None:
    pass


def selectbox(
    label: str,
    options: Sequence[Any],
    index: int = 0,
    *,
    key: Optional[str] = None,
    **_kwargs: Any,
) -> Any:
    chosen_key = key or label
    if chosen_key in session_state:
        value = session_state[chosen_key]
    else:
        try:
            value = options[index]
        except Exception:
            value = options[0] if options else None
        session_state[chosen_key] = value
    return _record_widget(_Widget("selectbox", label, options=list(options), value=value)).value


def multiselect(
    label: str,
    options: Sequence[Any],
    *,
    default: Optional[Sequence[Any]] = None,
    key: Optional[str] = None,
    **_kwargs: Any,
) -> List[Any]:
    chosen_key = key or label
    if chosen_key in session_state:
        value = list(session_state[chosen_key])
    else:
        value = list(default) if default is not None else []
        session_state[chosen_key] = value
    widget = _Widget("multiselect", label, options=list(options), value=list(value))
    _record_widget(widget)
    return widget.value


def text_input(
    label: str,
    value: str = "",
    *,
    key: Optional[str] = None,
    **_kwargs: Any,
) -> str:
    chosen_key = key or label
    if chosen_key in session_state:
        result = str(session_state[chosen_key])
    else:
        result = str(value)
        session_state[chosen_key] = result
    return result


def slider(
    label: str,
    min_value: int,
    max_value: int,
    *,
    value: Optional[int] = None,
    step: int = 1,
    key: Optional[str] = None,
    **_kwargs: Any,
) -> int:
    chosen_key = key or label
    if chosen_key in session_state:
        result = int(session_state[chosen_key])
    else:
        result = int(value if value is not None else min_value)
        session_state[chosen_key] = result
    return result


def checkbox(
    label: str,
    *,
    value: bool = False,
    key: Optional[str] = None,
    **_kwargs: Any,
) -> bool:
    chosen_key = key or label
    if chosen_key in session_state:
        result = bool(session_state[chosen_key])
    else:
        result = bool(value)
        session_state[chosen_key] = result
    return result


def _trigger_key(label: str, key: Optional[str]) -> str:
    return f"__trigger__:{key or label}"


def button(label: str, *, key: Optional[str] = None, **_kwargs: Any) -> bool:
    trigger_key = _trigger_key(label, key)
    if session_state.pop(trigger_key, False):
        return True
    return False


def download_button(
    _label: str,
    _data: Any,
    *,
    file_name: str,
    mime: str,
    disabled: bool = False,
    **_kwargs: Any,
) -> bool:
    return not disabled


class _Progress:
    def progress(self, _value: int, **_kwargs: Any) -> None:
        pass


class _Status:
    def update(self, **_kwargs: Any) -> None:
        pass


def progress(_value: int, **_kwargs: Any) -> _Progress:
    return _Progress()


def status(_label: str, **_kwargs: Any) -> _Status:
    return _Status()


def tabs(labels: Sequence[str]) -> Tuple[_Context, ...]:
    return tuple(_Context(f"tab:{label}") for label in labels)


def columns(count: int) -> Tuple[_Context, ...]:
    return tuple(_Context(f"column:{idx}") for idx in range(count))


def columns_from_list(labels: Sequence[str]) -> Tuple[_Context, ...]:  # pragma: no cover
    return tuple(_Context(f"column:{label}") for label in labels)


__all__ = [
    "session_state",
    "cache_data",
    "set_page_config",
    "title",
    "header",
    "subheader",
    "caption",
    "write",
    "markdown",
    "info",
    "warning",
    "error",
    "success",
    "json",
    "dataframe",
    "code",
    "selectbox",
    "multiselect",
    "text_input",
    "slider",
    "checkbox",
    "button",
    "download_button",
    "tabs",
    "columns",
    "progress",
    "status",
    "sidebar",
]
