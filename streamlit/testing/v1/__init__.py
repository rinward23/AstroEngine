"""Test harness stub for ``streamlit.testing.v1``."""

from __future__ import annotations

import runpy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import streamlit as st


def _reset_widgets() -> None:
    st._WIDGETS["main"].clear()  # type: ignore[attr-defined]
    st._WIDGETS["sidebar"].clear()  # type: ignore[attr-defined]
    st._CURRENT_CONTAINER[:] = ["main"]  # type: ignore[attr-defined]


def _run_app(path: Path) -> None:
    _reset_widgets()
    runpy.run_path(str(path), run_name="__main__")


@dataclass
class _WidgetHandle:
    widget: st._Widget  # type: ignore[attr-defined]

    @property
    def options(self) -> list[Any]:
        return list(self.widget.options or [])

    @property
    def value(self) -> Any:
        return self.widget.value


class _SidebarAccessor:
    def __init__(self, app: "AppTest") -> None:
        self.app = app

    def multiselect(self, label: str) -> _WidgetHandle:
        widget = st._WIDGETS["sidebar"].get(label)  # type: ignore[attr-defined]
        if widget is None:
            raise KeyError(f"No sidebar multiselect recorded for {label!r}")
        return _WidgetHandle(widget)


class _ButtonHandle:
    def __init__(self, app: "AppTest", label: str, key: str | None = None) -> None:
        self.app = app
        self.label = label
        self.key = key

    def click(self) -> "AppTest":
        trigger_key = st._trigger_key(self.label, self.key)  # type: ignore[attr-defined]
        st.session_state[trigger_key] = True
        return self.app


class AppTest:
    """Very small subset of Streamlit's testing harness."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.sidebar = _SidebarAccessor(self)

    @classmethod
    def from_file(cls, path: str | Path) -> "AppTest":
        app = cls(Path(path))
        app.run()
        return app

    def run(self, timeout: float | None = None) -> "AppTest":  # pragma: no cover - timeout ignored
        _run_app(self.path)
        return self

    def button(self, label: str, *, key: str | None = None) -> _ButtonHandle:
        return _ButtonHandle(self, label, key=key)

    @property
    def session_state(self) -> Dict[str, Any]:
        return st.session_state


__all__ = ["AppTest"]
