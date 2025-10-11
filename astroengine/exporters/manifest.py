"""Helpers for writing manifest payloads alongside dataset exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

SCHEMA_URI = "https://astro.engine/schemas/export_manifest_v1.json"
SCHEMA_ID = "astroengine.export.manifest"
SCHEMA_VERSION = "v1.0.0"

__all__ = [
    "ExportManifestBuilder",
    "manifest_path_for",
]


@dataclass
class _FileRecord:
    path: str
    bytes: int
    sha256: str


class _EventMetadataCollector:
    """Accumulate metadata observed while streaming events."""

    def __init__(self) -> None:
        self.profile_ids: set[str] = set()
        self.natal_ids: set[str] = set()
        self.providers: set[str] = set()
        self._window_start: str | None = None
        self._window_end: str | None = None
        self.event_count: int = 0

    def observe(self, event: Any) -> None:
        mapping = _coerce_mapping(event)
        self.event_count += 1
        self._record_profile(mapping)
        self._record_natal(mapping)
        self._record_provider(mapping)
        self._record_window(mapping)
        meta = mapping.get("meta")
        if isinstance(meta, Mapping):
            self._record_profile(meta)
            self._record_natal(meta)
            self._record_provider(meta)
            self._record_window(meta)

    def _record_profile(self, mapping: Mapping[str, Any]) -> None:
        candidate = _extract_profile_id(mapping)
        if candidate:
            self.profile_ids.add(candidate)

    def _record_natal(self, mapping: Mapping[str, Any]) -> None:
        candidate = _extract_natal_id(mapping)
        if candidate:
            self.natal_ids.add(candidate)

    def _record_provider(self, mapping: Mapping[str, Any]) -> None:
        candidate = mapping.get("provider") or mapping.get("provider_id")
        if isinstance(candidate, str) and candidate.strip():
            self.providers.add(candidate.strip())

    def _record_window(self, mapping: Mapping[str, Any]) -> None:
        for start, end in _extract_windows(mapping):
            if start:
                if self._window_start is None or start < self._window_start:
                    self._window_start = start
            if end:
                if self._window_end is None or end > self._window_end:
                    self._window_end = end

    def snapshot(self) -> dict[str, Any]:
        return {
            "profile_ids": sorted(self.profile_ids),
            "natal_ids": sorted(self.natal_ids),
            "providers": sorted(self.providers),
            "event_count": self.event_count,
            "window_start": self._window_start,
            "window_end": self._window_end,
        }


class ExportManifestBuilder:
    """Compute and persist export manifest payloads."""

    def __init__(self, events: Iterable[Any] | None = None) -> None:
        self._collector = _EventMetadataCollector()
        if events is not None:
            self.collect(events)

    def collect(self, events: Iterable[Any]) -> None:
        for event in events:
            self._collector.observe(event)

    def wrap(self, events: Iterable[Any]) -> Iterable[Any]:
        for event in events:
            self._collector.observe(event)
            yield event

    def record_profile(self, profile_id: str | None) -> None:
        if isinstance(profile_id, str) and profile_id.strip():
            self._collector.profile_ids.add(profile_id.strip())

    def record_window(self, start: str | None, end: str | None) -> None:
        if start and (self._collector._window_start is None or start < self._collector._window_start):
            self._collector._window_start = start
        if end and (self._collector._window_end is None or end > self._collector._window_end):
            self._collector._window_end = end

    def write(
        self,
        output_path: str | Path,
        *,
        fmt: str,
        rows: int | None = None,
        explicit_window: tuple[str | None, str | None] | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> Path:
        """Write the manifest adjacent to ``output_path`` and return its path."""

        output = Path(output_path)
        manifest_path = manifest_path_for(output)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._build_payload(
            output=output,
            manifest_path=manifest_path,
            fmt=fmt,
            rows=rows,
            explicit_window=explicit_window,
            meta=meta,
        )
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def _build_payload(
        self,
        *,
        output: Path,
        manifest_path: Path,
        fmt: str,
        rows: int | None,
        explicit_window: tuple[str | None, str | None] | None,
        meta: Mapping[str, Any] | None,
    ) -> MutableMapping[str, Any]:
        snapshot = self._collector.snapshot()
        start = snapshot["window_start"]
        end = snapshot["window_end"]
        if explicit_window is not None:
            exp_start, exp_end = explicit_window
            if exp_start:
                start = exp_start
            if exp_end:
                end = exp_end
        outputs = [_describe_output(output, fmt, rows, manifest_path.parent)]
        payload: dict[str, Any] = {
            "$schema": SCHEMA_URI,
            "schema": {
                "id": SCHEMA_ID,
                "version": SCHEMA_VERSION,
            },
            "generated_at": _now_iso(),
            "profile_ids": snapshot["profile_ids"],
            "natal_ids": snapshot["natal_ids"],
            "scan_window": None,
            "outputs": outputs,
            "meta": {
                "event_count": snapshot["event_count"],
                "providers": snapshot["providers"],
            },
        }
        if start or end:
            payload["scan_window"] = {
                "start": start,
                "end": end,
            }
        if meta:
            payload["meta"].update(_sanitize_meta(meta))
        payload["meta"] = _compact_meta(payload["meta"])
        return payload


def manifest_path_for(output_path: str | Path) -> Path:
    path = Path(output_path)
    return path.with_name(path.name + ".manifest.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_mapping(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, Mapping):
        return obj
    if hasattr(obj, "__dict__"):
        return dict(vars(obj))
    return {}


def _extract_profile_id(mapping: Mapping[str, Any]) -> str | None:
    for key in ("profile_id", "profileId"):
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    profile = mapping.get("profile")
    if isinstance(profile, str) and profile.strip():
        return profile.strip()
    if isinstance(profile, Mapping):
        for key in ("id", "profile_id", "profileId"):
            value = profile.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_natal_id(mapping: Mapping[str, Any]) -> str | None:
    for key in ("natal_id", "natalId", "subject_ref", "subjectRef"):
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    subject = mapping.get("subject")
    if isinstance(subject, Mapping):
        for key in ("id", "natal_id", "natalId"):
            value = subject.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_windows(mapping: Mapping[str, Any]) -> list[tuple[str | None, str | None]]:
    windows: list[tuple[str | None, str | None]] = []
    for key in ("window", "window_utc", "scan_window", "scanWindow", "windowUtc"):
        value = mapping.get(key)
        candidate = _coerce_window(value)
        if candidate:
            windows.append(candidate)
    starts = [
        mapping.get("window_start"),
        mapping.get("window_start_utc"),
        mapping.get("scan_window_start"),
        mapping.get("scan_window_start_utc"),
    ]
    ends = [
        mapping.get("window_end"),
        mapping.get("window_end_utc"),
        mapping.get("scan_window_end"),
        mapping.get("scan_window_end_utc"),
    ]
    start = _first_str(starts)
    end = _first_str(ends)
    if start or end:
        windows.append((start, end))
    return windows


def _coerce_window(value: Any) -> tuple[str | None, str | None] | None:
    if not isinstance(value, Mapping):
        return None
    start = _first_str(
        [
            value.get("start"),
            value.get("start_utc"),
            value.get("begin"),
            value.get("from"),
        ]
    )
    end = _first_str(
        [
            value.get("end"),
            value.get("end_utc"),
            value.get("finish"),
            value.get("to"),
        ]
    )
    if start or end:
        return (start, end)
    return None


def _first_str(values: Sequence[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _describe_output(
    output: Path,
    fmt: str,
    rows: int | None,
    base_dir: Path,
) -> dict[str, Any]:
    if output.is_dir():
        files = _directory_records(output)
        checksum = _combined_checksum(files)
        total_bytes = sum(record.bytes for record in files)
        payload: dict[str, Any] = {
            "format": fmt,
            "path": _relative_path(output, base_dir),
            "bytes": total_bytes,
            "checksum": {"sha256": checksum},
            "rows": rows,
            "files": [
                {
                    "path": record.path,
                    "bytes": record.bytes,
                    "sha256": record.sha256,
                }
                for record in files
            ],
        }
        if rows is None:
            payload.pop("rows")
        return payload

    if not output.exists():
        raise FileNotFoundError(output)
    data = output.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    payload = {
        "format": fmt,
        "path": _relative_path(output, base_dir),
        "bytes": len(data),
        "checksum": {"sha256": digest},
    }
    if rows is not None:
        payload["rows"] = rows
    return payload


def _directory_records(root: Path) -> list[_FileRecord]:
    records: list[_FileRecord] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        records.append(
            _FileRecord(path=rel, bytes=len(data), sha256=digest)
        )
    return records


def _combined_checksum(records: Sequence[_FileRecord]) -> str:
    hasher = hashlib.sha256()
    for record in records:
        hasher.update(record.path.encode("utf-8"))
        hasher.update(record.sha256.encode("ascii"))
    return hasher.hexdigest()


def _relative_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _sanitize_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in meta.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, Mapping):
            sanitized[key] = _sanitize_meta(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            sanitized[key] = [
                item
                for item in (
                    _sanitize_meta(item) if isinstance(item, Mapping) else item
                    for item in value
                )
                if isinstance(item, (str, int, float, bool)) or item is None or isinstance(item, Mapping)
            ]
        else:
            sanitized[key] = str(value)
    return sanitized


def _compact_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in meta.items():
        if value in (None, [], {}):
            continue
        compact[key] = value
    return compact
