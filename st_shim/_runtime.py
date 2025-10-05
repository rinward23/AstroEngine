"""Minimal runtime primitives backing the Streamlit testing shim."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ButtonWidget",
    "MultiSelectWidget",
    "StreamlitRuntime",
    "Widget",
]


@dataclass
class Widget:
    runtime: StreamlitRuntime
    kind: str
    key: str
    label: str


class ButtonWidget(Widget):
    """Button widget supporting queued click events."""

    _app: Any | None = None

    @property
    def value(self) -> bool:
        return bool(self.runtime.widget_values.get(self.key, False))

    def click(self) -> Any:
        self.runtime.schedule_click(self.key)
        if self._app is None:
            return None
        return self._app


class MultiSelectWidget(Widget):
    """Multiselect widget exposing options for inspection."""

    options: list[str]

    def __init__(
        self,
        runtime: StreamlitRuntime,
        kind: str,
        key: str,
        label: str,
        options: Iterable[str],
    ) -> None:
        super().__init__(runtime=runtime, kind=kind, key=key, label=label)
        self.options = list(options)

    @property
    def value(self) -> list[str]:
        value = self.runtime.session_state.get(self.key, [])
        if isinstance(value, list):
            return list(value)
        return list(value or [])


class StreamlitRuntime:
    """Tracks widget state and session state for the shim."""

    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.widgets: dict[str, Widget] = {}
        self.widgets_by_label: dict[str, list[Widget]] = {}
        self.widget_values: dict[str, Any] = {}
        self._pending_clicks: set[str] = set()
        self._active_clicks: set[str] = set()

    def prepare_for_run(self) -> None:
        self.widgets = {}
        self.widgets_by_label = {}
        self.widget_values = {}
        self._active_clicks = set(self._pending_clicks)

    def register(self, widget: Widget) -> Widget:
        self.widgets[widget.key] = widget
        self.widgets_by_label.setdefault(widget.label, []).append(widget)
        return widget

    def schedule_click(self, key: str) -> None:
        self._pending_clicks.add(key)

    def consume_click(self, key: str) -> bool:
        if key in self._active_clicks:
            self._active_clicks.remove(key)
            self._pending_clicks.discard(key)
            return True
        return False

    def store_value(self, key: str, value: Any) -> None:
        self.widget_values[key] = value

    def find_widget(
        self, kind: str, label: str, key: str | None = None
    ) -> Widget | None:
        if key is not None:
            widget = self.widgets.get(key)
            if widget is not None and widget.kind == kind:
                return widget
        widgets = self.widgets_by_label.get(label, [])
        for widget in reversed(widgets):
            if widget.kind == kind:
                return widget
        return None
