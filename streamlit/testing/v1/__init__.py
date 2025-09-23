"""Lightweight Streamlit testing stub for unit tests."""

from __future__ import annotations

import runpy
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

__all__ = ["AppTest"]


class _SessionState(dict):
    def setdefault(self, key: str, default: Any) -> Any:  # type: ignore[override]
        return super().setdefault(key, default)


class _WidgetRegistry:
    def __init__(self) -> None:
        self._containers: Dict[str, Dict[str, Any]] = {"main": {}, "sidebar": {}}

    def register(self, container: str, label: str, widget: Any) -> Any:
        self._containers.setdefault(container, {})[label] = widget
        return widget

    def get(self, container: str, label: str) -> Any:
        return self._containers.get(container, {}).get(label)


class _WidgetCollection:
    def __init__(self, app: "AppTest", container: str) -> None:
        self._app = app
        self._container = container

    def multiselect(self, label: str) -> "_FakeMultiselect":
        widget = self._app._widgets.get(self._container, label)
        if widget is None:
            raise KeyError(label)
        if not isinstance(widget, _FakeMultiselect):
            raise KeyError(label)
        return widget

    def selectbox(self, label: str) -> "_FakeSelect":
        widget = self._app._widgets.get(self._container, label)
        if widget is None:
            raise KeyError(label)
        if not isinstance(widget, _FakeSelect):
            raise KeyError(label)
        return widget

    def text_input(self, label: str) -> "_FakeTextInput":
        widget = self._app._widgets.get(self._container, label)
        if widget is None:
            raise KeyError(label)
        if not isinstance(widget, _FakeTextInput):
            raise KeyError(label)
        return widget


@dataclass
class _FakeMultiselect:
    label: str
    options: List[str]
    value: List[str]

    def select(self, values: Iterable[str]) -> None:
        self.value = [val for val in values if val in self.options]


@dataclass
class _FakeSelect:
    label: str
    options: List[str]
    value: str


@dataclass
class _FakeTextInput:
    label: str
    value: str


class _FakeButton:
    def __init__(self, label: str, app: "AppTest") -> None:
        self.label = label
        self._app = app

    def click(self) -> "AppTest":
        self._app._button_queue.append(self.label)
        return self._app


class _FakeProgress:
    def progress(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeStatus:
    def update(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
        return None


class _FakeTabs(List["_FakeTab"]):
    pass


class _FakeTab:
    def __init__(self, app: "AppTest") -> None:
        self._app = app

    def __enter__(self) -> "_FakeTab":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None


class _FakeColumns(List["_FakeColumn"]):
    pass


class _FakeColumn:
    def __init__(self, module: "_FakeStreamlit", container: str) -> None:
        self._module = module
        self._container = container

    def __enter__(self) -> "_FakeColumn":  # pragma: no cover - context manager convenience
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:  # pragma: no cover - context manager convenience
        return False

    def text_input(self, *args: Any, **kwargs: Any) -> str:
        return self._module._input(self._container, _FakeTextInput, *args, **kwargs)

    def button(self, *args: Any, **kwargs: Any) -> bool:
        return self._module.button(*args, container=self._container, **kwargs)

    def download_button(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeSidebar:
    def __init__(self, module: "_FakeStreamlit") -> None:
        self._module = module

    def header(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def selectbox(self, *args: Any, **kwargs: Any) -> str:
        return self._module._select("sidebar", *args, **kwargs)

    def multiselect(self, *args: Any, **kwargs: Any) -> List[str]:
        return self._module._multiselect("sidebar", *args, **kwargs)

    def text_input(self, *args: Any, **kwargs: Any) -> str:
        return self._module._input("sidebar", _FakeTextInput, *args, **kwargs)

    def slider(self, *args: Any, **kwargs: Any) -> int:
        return self._module.slider(*args, container="sidebar", **kwargs)

    def checkbox(self, *args: Any, **kwargs: Any) -> bool:
        return self._module.checkbox(*args, container="sidebar", **kwargs)


class _FakeStreamlit(types.ModuleType):
    def __init__(self, app: "AppTest") -> None:
        super().__init__("streamlit")
        self._app = app
        self.session_state = app.session_state
        self.sidebar = _FakeSidebar(self)

    # no-op UI helpers -------------------------------------------------
    def set_page_config(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def title(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def header(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def subheader(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def success(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def json(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def dataframe(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def code(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def download_button(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    # inputs ------------------------------------------------------------
    def _input(self, container: str, widget_cls, label: str, *, key: str | None = None, value: Any = "", **_kwargs: Any) -> Any:
        if key is not None:
            current = self.session_state.get(key, value)
            self.session_state[key] = current
            widget = widget_cls(label=label, value=current)
        else:
            widget = widget_cls(label=label, value=value)
        self._app._widgets.register(container, label, widget)
        return widget.value

    def text_input(self, *args: Any, **kwargs: Any) -> str:
        return self._input("main", _FakeTextInput, *args, **kwargs)

    def selectbox(
        self,
        label: str,
        options: Iterable[Any],
        *,
        index: int = 0,
        key: str | None = None,
        **_kwargs: Any,
    ) -> str:
        return self._select("main", label, options, index=index, key=key)

    def _select(
        self,
        container: str,
        label: str,
        options: Iterable[Any],
        *,
        index: int = 0,
        key: str | None = None,
        **_kwargs: Any,
    ) -> str:
        options_list = list(options)
        if not options_list:
            value = ""
        else:
            value = options_list[min(max(index, 0), len(options_list) - 1)]
        if key is not None:
            current = self.session_state.get(key, value)
            self.session_state[key] = current
        widget = _FakeSelect(label=label, options=[str(opt) for opt in options_list], value=str(value))
        self._app._widgets.register(container, label, widget)
        return widget.value

    def _multiselect(
        self,
        container: str,
        label: str,
        options: Iterable[Any],
        *,
        default: Iterable[Any] | None = None,
        key: str | None = None,
        **_kwargs: Any,
    ) -> List[str]:
        option_list = [str(opt) for opt in options]
        default_values = [str(val) for val in (default or []) if str(val) in option_list]
        if key is not None:
            current = list(self.session_state.get(key, default_values))
            self.session_state[key] = current
            value = current
        else:
            value = default_values
        widget = _FakeMultiselect(label=label, options=option_list, value=list(value))
        self._app._widgets.register(container, label, widget)
        return widget.value

    def multiselect(self, *args: Any, **kwargs: Any) -> List[str]:
        return self._multiselect("main", *args, **kwargs)

    def slider(self, label: str, *, min_value: int, max_value: int, value: int, step: int, key: str | None = None, **_kwargs: Any) -> int:
        if key is not None:
            current = int(self.session_state.get(key, value))
            self.session_state[key] = current
        else:
            current = value
        widget = _FakeSelect(label=label, options=[str(v) for v in range(min_value, max_value + 1, step)], value=str(current))
        self._app._widgets.register(_kwargs.pop("container", "main"), label, widget)
        return current

    def checkbox(
        self,
        label: str,
        *,
        value: bool = False,
        key: str | None = None,
        **_kwargs: Any,
    ) -> bool:
        if key is not None:
            current = bool(self.session_state.get(key, value))
            self.session_state[key] = current
        else:
            current = value
        widget = _FakeSelect(label=label, options=["True", "False"], value=str(current))
        self._app._widgets.register(_kwargs.pop("container", "main"), label, widget)
        return current

    def button(self, label: str, *, container: str = "main", key: str | None = None, **_kwargs: Any) -> bool:
        widget = _FakeButton(label=label, app=self._app)
        self._app._widgets.register(container, label, widget)
        pressed = self._app._consume_button_press(label)
        if key is not None:
            self.session_state[key] = pressed
        return pressed

    def progress(self, *_args: Any, **_kwargs: Any) -> _FakeProgress:
        return _FakeProgress()

    def status(self, *_args: Any, **_kwargs: Any) -> _FakeStatus:
        return _FakeStatus()

    def tabs(self, labels: Iterable[str]) -> _FakeTabs:
        return _FakeTabs([_FakeTab(self._app) for _ in labels])

    def columns(self, n: int) -> _FakeColumns:
        return _FakeColumns([_FakeColumn(self, "main") for _ in range(n)])

    def cache_data(self, *_args: Any, **_kwargs: Any):
        def decorator(func):
            return func

        return decorator


class AppTest:
    """Minimal AppTest harness for Streamlit unit tests."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.session_state: _SessionState = _SessionState()
        self._widgets = _WidgetRegistry()
        self._button_queue: List[str] = []
        self.exception: Exception | None = None

    @classmethod
    def from_file(cls, path: str) -> "AppTest":
        return cls(Path(path))

    def _consume_button_press(self, label: str) -> bool:
        if label in self._button_queue:
            self._button_queue.remove(label)
            return True
        return False

    def _register_widget(self, container: str, label: str, widget: Any) -> Any:
        return self._widgets.register(container, label, widget)

    @property
    def sidebar(self) -> _WidgetCollection:
        return _WidgetCollection(self, "sidebar")

    def button(self, label: str) -> _FakeButton:
        widget = self._widgets.get("main", label)
        if widget is None or not isinstance(widget, _FakeButton):
            raise KeyError(label)
        return widget

    def run(self, timeout: float | None = None) -> "AppTest":  # noqa: ARG002 - timeout unused
        original = sys.modules.get("streamlit")
        self._widgets = _WidgetRegistry()
        fake = _FakeStreamlit(self)
        sys.modules["streamlit"] = fake
        self.exception = None
        try:
            runpy.run_path(str(self._path), run_name="__main__")
        except Exception as exc:  # pragma: no cover - surfaced to tests
            self.exception = exc
        finally:
            if original is not None:
                sys.modules["streamlit"] = original
            else:  # pragma: no cover - defensive cleanup
                sys.modules.pop("streamlit", None)
        return self

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"AppTest(path={self._path!s})"
