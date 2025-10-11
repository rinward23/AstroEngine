"""Utilities for persisting dashboard layout settings for the Streamlit portal."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
LAYOUT_FILE = ROOT_DIR / "profiles" / "dashboard_layout.json"
DEFAULT_LAYOUT_NAME = "default"

LayoutPayload = Dict[str, Any]


def _read_layout_file() -> dict[str, LayoutPayload]:
    """Return the saved layouts from disk, ignoring malformed entries."""
    if not LAYOUT_FILE.exists():
        return {}
    try:
        with LAYOUT_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    valid_layouts: dict[str, LayoutPayload] = {}
    for name, payload in data.items():
        if isinstance(name, str) and isinstance(payload, dict):
            valid_layouts[name] = payload
    return valid_layouts


def list_layouts() -> list[str]:
    """Return available layout names with the built-in default listed first."""
    layouts = sorted(_read_layout_file().keys())
    if DEFAULT_LAYOUT_NAME in layouts:
        layouts.remove(DEFAULT_LAYOUT_NAME)
    layouts.insert(0, DEFAULT_LAYOUT_NAME)
    return layouts


def load_layout(name: str = DEFAULT_LAYOUT_NAME) -> LayoutPayload | None:
    """Load a named layout from disk, returning a deep copy to avoid mutation."""
    normalized = (name or DEFAULT_LAYOUT_NAME).strip() or DEFAULT_LAYOUT_NAME
    layouts = _read_layout_file()
    payload = layouts.get(normalized)
    if payload is None:
        return None
    return deepcopy(payload)


def save_layout(name: str, payload: LayoutPayload) -> None:
    """Persist the given layout under the provided name."""
    name = name.strip() or DEFAULT_LAYOUT_NAME
    layouts = _read_layout_file()
    layouts[name] = deepcopy(payload)
    LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LAYOUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(layouts, handle, ensure_ascii=False, indent=2, sort_keys=True)
