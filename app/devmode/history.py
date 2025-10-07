"""Utilities for maintaining developer-mode version history."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

HISTORY_FILE = Path(".astroengine/version_history.json")
CHANGELOG_FILE = Path("CHANGELOG.md")


@dataclass
class Entry:
    """Record describing a dev mode patch application."""

    ts: float
    user: str
    commit: str
    message: str
    snapshot: str
    touched_files: list[str]
    core_edited: bool


def _history_path(root: str | Path) -> Path:
    return Path(root) / HISTORY_FILE


def read_history(root: str | Path = ".") -> list[dict]:
    """Return the recorded dev history entries for *root*."""

    path = _history_path(root)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Corrupt history should not break the UI; surface an empty list.
        return []


def append_history(entry: Entry, root: str | Path = ".") -> None:
    """Append *entry* to the JSON history ledger."""

    path = _history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    items = read_history(root)
    items.append(asdict(entry))
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def append_changelog(message: str, commit: str, root: str | Path = ".") -> None:
    """Record a changelog entry summarising a dev patch."""

    path = Path(root) / CHANGELOG_FILE
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"\n- {timestamp} — {message} (`{commit[:7]}`)"
    if path.exists():
        original = path.read_text(encoding="utf-8")
        path.write_text(original + line + "\n", encoding="utf-8")
    else:
        header = "# Changelog\n"
        path.write_text(header + line + "\n", encoding="utf-8")
