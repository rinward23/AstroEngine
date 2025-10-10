"""Lightweight journaling helpers for narrative conversations."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from ..infrastructure.home import ae_home
from ..utils.i18n import translate

__all__ = [
    "JournalEntry",
    "log_entry",
    "load_entry",
    "list_entries",
    "latest_entries",
    "iter_entries",
    "journal_prompt_lines",
    "journal_template_lines",
    "journal_context_payload",
]

_JOURNAL_DIR = ae_home() / "journal"


def _ensure_dir() -> Path:
    _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    return _JOURNAL_DIR


def _entry_path(entry_id: str) -> Path:
    return _ensure_dir() / f"{entry_id}.json"


def _now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_tags(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    seen: dict[str, None] = {}
    for tag in tags:
        if not tag:
            continue
        key = str(tag).strip()
        if key:
            seen[key] = None
    return sorted(seen.keys())


def _shorten(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


@dataclass(slots=True)
class JournalEntry:
    """Serialized representation of a chatbot exchange."""

    entry_id: str
    prompt: str
    response: str
    created_at: str = field(default_factory=_now)
    model: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        payload["metadata"] = dict(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "JournalEntry":
        tags = payload.get("tags")
        metadata = payload.get("metadata")
        return cls(
            entry_id=str(payload["entry_id"]),
            prompt=str(payload.get("prompt", "")),
            response=str(payload.get("response", "")),
            created_at=str(payload.get("created_at", _now())),
            model=payload.get("model"),
            tags=_sanitize_tags(tags if isinstance(tags, Iterable) else []),
            metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
        )


def log_entry(
    prompt: str,
    response: str,
    *,
    entry_id: str | None = None,
    created_at: str | None = None,
    model: str | None = None,
    tags: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> JournalEntry:
    """Persist a journal record and return the resulting :class:`JournalEntry`."""

    entry = JournalEntry(
        entry_id=entry_id or os.urandom(8).hex(),
        prompt=prompt,
        response=response,
        created_at=created_at or _now(),
        model=model,
        tags=_sanitize_tags(tags),
        metadata=dict(metadata or {}),
    )
    path = _entry_path(entry.entry_id)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entry.to_dict(), handle, indent=2, ensure_ascii=False)
    return entry


def load_entry(entry_id: str) -> JournalEntry:
    """Load a single journal entry by identifier."""

    path = _entry_path(entry_id)
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Journal entry {entry_id} is malformed")
    return JournalEntry.from_dict(payload)


def iter_entries(*, reverse: bool = True) -> Iterator[JournalEntry]:
    """Yield journal entries sorted by timestamp."""

    files = sorted(_ensure_dir().glob("*.json"))
    entries = (load_entry(path.stem) for path in files)
    ordered = sorted(entries, key=lambda item: item.created_at, reverse=reverse)
    for entry in ordered:
        yield entry


def list_entries(limit: int | None = None) -> list[JournalEntry]:
    """Return a list of journal entries respecting ``limit``."""

    results: list[JournalEntry] = []
    for entry in iter_entries():
        results.append(entry)
        if limit is not None and len(results) >= limit:
            break
    return results


def latest_entries(limit: int = 3, *, tags: Iterable[str] | None = None) -> list[JournalEntry]:
    """Return the newest journal entries, optionally filtered by ``tags``."""

    if tags:
        wanted = {str(tag).strip() for tag in tags if tag}
    else:
        wanted = None
    results: list[JournalEntry] = []
    for entry in iter_entries():
        if wanted and not wanted.intersection(entry.tags):
            continue
        results.append(entry)
        if len(results) >= limit:
            break
    return results


def journal_prompt_lines(
    entries: Sequence[JournalEntry],
    *,
    locale: str | None = None,
) -> list[str]:
    """Return translated lines summarizing ``entries`` for LLM prompts."""

    if not entries:
        return []
    lines = [translate("narrative.prompt.journal_header", locale=locale)]
    for entry in entries:
        tags = ", ".join(entry.tags)
        tag_suffix = f" [{tags}]" if tags else ""
        summary = _shorten(entry.response)
        lines.append(
            translate(
                "narrative.prompt.journal_line",
                locale=locale,
                timestamp=entry.created_at,
                summary=summary,
                tags=tag_suffix,
            )
        )
    return lines


def journal_template_lines(
    entries: Sequence[JournalEntry],
    *,
    locale: str | None = None,
) -> list[str]:
    """Return deterministic lines for offline templates."""

    if not entries:
        return []
    lines = [translate("narrative.template.journal_header", locale=locale)]
    for entry in entries:
        tags = ", ".join(entry.tags)
        tag_suffix = f" [{tags}]" if tags else ""
        summary = _shorten(entry.response, limit=240)
        lines.append(
            translate(
                "narrative.template.journal_line",
                locale=locale,
                timestamp=entry.created_at,
                summary=summary,
                tags=tag_suffix,
            )
        )
    return lines


def journal_context_payload(
    entries: Sequence[JournalEntry],
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return context keys suitable for :func:`render_profile`."""

    lines = journal_template_lines(entries, locale=locale)
    if not lines:
        return {}
    header, *body = lines
    return {
        "journal_header": header,
        "journal_excerpt_lines": body,
        "journal_count": len(entries),
    }

