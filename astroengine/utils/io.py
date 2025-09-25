"""Shared I/O helpers for working with repository data files."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

__all__ = ["load_json_document"]


_DEFAULT_SENTINEL = object()


def _filtered_lines(text: str, prefixes: Sequence[str]) -> Iterable[str]:
    """Yield ``text`` lines excluding those that start with *prefixes* after stripping.

    The repository stores a number of JSON documents that include comment lines
    beginning with ``#`` (or other prefixes).  Several modules previously
    duplicated the same filtering logic before calling :func:`json.loads`.  This
    helper centralises the behaviour and guarantees consistent handling of
    comment prefixes across the code base.
    """

    if not prefixes:
        yield from text.splitlines()
        return

    prefix_tuple = tuple(prefixes)
    for line in text.splitlines():
        if not line.strip().startswith(prefix_tuple):
            yield line


def load_json_document(
    path: str | Path,
    *,
    comment_prefixes: Sequence[str] = ("#",),
    default: Any = _DEFAULT_SENTINEL,
    encoding: str = "utf-8",
) -> Any:
    """Return JSON content from ``path`` while ignoring comment-prefixed lines.

    Args:
        path: Location of the JSON document to read.
        comment_prefixes: One or more prefixes that denote comment lines.  Lines
            whose stripped form starts with any of the prefixes are excluded.
        default: Optional fallback value returned when the resulting payload is
            empty after comment filtering.  When omitted, the function mirrors
            ``json.loads`` behaviour and raises a :class:`json.JSONDecodeError`
            for empty payloads.
        encoding: Text encoding used when reading ``path``.

    Returns:
        The deserialised JSON content (typically a ``dict`` or ``list``).
    """

    payload_path = Path(path)
    text = payload_path.read_text(encoding=encoding)
    payload = "\n".join(_filtered_lines(text, comment_prefixes))

    if not payload.strip():
        if default is _DEFAULT_SENTINEL:
            # Match the previous behaviour by delegating to ``json.loads`` to
            # raise ``JSONDecodeError`` when no content is present.
            return json.loads(payload)
        return default

    return json.loads(payload)
