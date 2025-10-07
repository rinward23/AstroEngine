"""Subset of :mod:`streamlit.testing.v1` required by the test-suite."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

from .. import set_runtime
from .._runtime import ButtonWidget, MultiSelectWidget, StreamlitRuntime

__all__ = ["AppTest"]


class _SidebarAccessor:
    def __init__(self, app: AppTest) -> None:
        self._app = app

    def multiselect(self, label: str, *, key: str | None = None) -> MultiSelectWidget:
        widget = self._app._runtime.find_widget("multiselect", label, key)
        if widget is None:
            raise KeyError(f"multiselect '{label}' not available")
        widget._app = self._app
        return widget  # type: ignore[return-value]


class _ButtonAccessor:
    def __init__(self, app: AppTest) -> None:
        self._app = app

    def __call__(self, label: str, *, key: str | None = None) -> ButtonWidget:
        widget = self._app._runtime.find_widget("button", label, key)
        if widget is None:
            raise KeyError(f"button '{label}' not available")
        widget._app = self._app
        return widget  # type: ignore[return-value]


class AppTest:
    """Very small harness that executes Streamlit scripts in-process."""

    def __init__(self, path: Path, runtime: StreamlitRuntime) -> None:
        self._path = path
        self._runtime = runtime
        self.sidebar = _SidebarAccessor(self)
        self.button = _ButtonAccessor(self)

    @classmethod
    def from_file(cls, path: str | Path) -> AppTest:
        script_path = Path(path)
        if not script_path.exists():
            raise FileNotFoundError(script_path)
        runtime = StreamlitRuntime()
        return cls(script_path, runtime)

    def run(
        self, timeout: float | None = None
    ) -> AppTest:  # noqa: D401 - mimic Streamlit API
        del timeout  # not used; kept for API compatibility
        set_runtime(self._runtime)
        self._runtime.prepare_for_run()
        module_globals: dict[str, Any] = {
            "__name__": "__main__",
            "__file__": str(self._path),
        }
        runpy.run_path(str(self._path), run_name="__main__", init_globals=module_globals)
        return self

    @property
    def session_state(self) -> dict[str, Any]:
        return self._runtime.session_state
