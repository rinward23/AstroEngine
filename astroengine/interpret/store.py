"""Filesystem-backed rulepack store."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict

import yaml

from .loader import RulepackValidationError, load_rulepack
from .models import RulepackMeta, RulepackVersionPayload


@dataclass
class _RulepackVersion:
    version: int
    path: Path
    created_at: datetime
    mutable: bool


@dataclass
class _RulepackEntry:
    id: str
    name: str
    title: str
    description: str | None
    mutable: bool
    versions: dict[int, _RulepackVersion]


@dataclass
class _CachedRulepack:
    mtime: float
    payload: RulepackVersionPayload


def _iso_now() -> datetime:
    return datetime.now(tz=UTC)


def _compute_etag(content: Dict[str, Any]) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _dump_rulepack(content: Dict[str, Any]) -> str:
    return yaml.safe_dump(content, sort_keys=False, allow_unicode=True)


class RulepackStore:
    """Persisted rulepack catalogue with versioning support."""

    def __init__(
        self,
        *,
        base_dir: Path,
        builtin_dir: Path,
        allow_mutations: bool = False,
    ) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.builtin_dir = builtin_dir
        self.allow_mutations = allow_mutations
        self._builtin_entries = self._load_builtin_entries()
        self._cache: dict[tuple[str, int], _CachedRulepack] = {}

    # ------------------------------------------------------------------
    # Discovery helpers
    def _load_builtin_entries(self) -> dict[str, _RulepackEntry]:
        entries: dict[str, _RulepackEntry] = {}
        if not self.builtin_dir.exists():
            return entries
        for path in sorted(self.builtin_dir.glob("*.y*ml")) + sorted(
            self.builtin_dir.glob("*.json")
        ):
            try:
                raw = path.read_text(encoding="utf-8")
                loaded = load_rulepack(raw, source=str(path))
            except RulepackValidationError:
                continue
            header = loaded.document.meta
            version = int(header.version or 1)
            created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            entry = _RulepackEntry(
                id=header.id,
                name=header.name,
                title=header.title,
                description=header.description,
                mutable=False,
                versions={
                    version: _RulepackVersion(
                        version=version,
                        path=path,
                        created_at=created_at,
                        mutable=False,
                    )
                },
            )
            entries[entry.id] = entry
        return entries

    def _load_user_entries(self) -> dict[str, _RulepackEntry]:
        entries: dict[str, _RulepackEntry] = {}
        if not self.base_dir.exists():
            return entries
        for rp_dir in self.base_dir.iterdir():
            if not rp_dir.is_dir():
                continue
            meta_path = rp_dir / "meta.json"
            if not meta_path.exists():
                continue
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            versions: dict[int, _RulepackVersion] = {}
            for version_info in data.get("versions", []):
                try:
                    version = int(version_info["version"])
                    file_name = version_info.get("file") or f"v{version}.yaml"
                    created_at = datetime.fromisoformat(version_info["created_at"])
                except (KeyError, ValueError):
                    continue
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)
                else:
                    created_at = created_at.astimezone(UTC)
                path = rp_dir / file_name
                if not path.exists():
                    continue
                versions[version] = _RulepackVersion(
                    version=version,
                    path=path,
                    created_at=created_at,
                    mutable=True,
                )
            if not versions:
                continue
            entry = _RulepackEntry(
                id=data.get("id") or rp_dir.name,
                name=data.get("name") or data.get("id") or rp_dir.name,
                title=data.get("title") or data.get("name") or rp_dir.name,
                description=data.get("description"),
                mutable=True,
                versions=versions,
            )
            entries[entry.id] = entry
        return entries

    def _entries(self) -> dict[str, _RulepackEntry]:
        entries = dict(self._builtin_entries)
        entries.update(self._load_user_entries())
        return entries

    # ------------------------------------------------------------------
    def list_rulepacks(self) -> list[RulepackMeta]:
        metas: list[RulepackMeta] = []
        for entry in self._entries().values():
            latest_version = max(entry.versions)
            info = entry.versions[latest_version]
            available_versions = sorted(entry.versions)
            metas.append(
                RulepackMeta(
                    id=entry.id,
                    name=entry.name,
                    version=latest_version,
                    title=entry.title,
                    description=entry.description,
                    created_at=info.created_at,
                    mutable=entry.mutable,
                    available_versions=available_versions,
                )
            )
        metas.sort(key=lambda item: item.id)
        return metas

    def _load_version(self, entry: _RulepackEntry, version: int) -> RulepackVersionPayload:
        info = entry.versions.get(version)
        if info is None:
            raise KeyError(version)
        key = (entry.id, version)
        mtime = info.path.stat().st_mtime
        cached = self._cache.get(key)
        if cached and cached.mtime == mtime:
            return cached.payload
        raw = info.path.read_text(encoding="utf-8")
        loaded = load_rulepack(raw, source=str(info.path))
        content = loaded.content
        meta = RulepackMeta(
            id=entry.id,
            name=entry.name,
            version=version,
            title=entry.title,
            description=entry.description,
            created_at=info.created_at,
            mutable=entry.mutable,
            available_versions=sorted(entry.versions),
        )
        payload = RulepackVersionPayload(
            meta=meta,
            profiles=loaded.document.profiles,
            rules=loaded.document.rules,
            version=version,
            etag=_compute_etag(content),
            content=content,
            mutable=entry.mutable,
        )
        self._cache[key] = _CachedRulepack(mtime=mtime, payload=payload)
        return payload

    def get_rulepack(self, rulepack_id: str, version: int | None = None) -> RulepackVersionPayload:
        entries = self._entries()
        entry = entries.get(rulepack_id)
        if entry is None:
            raise KeyError(rulepack_id)
        if version is None:
            version = max(entry.versions)
        return self._load_version(entry, version)

    def save_rulepack(self, raw: str | bytes, *, source: str | None = None) -> RulepackMeta:
        loaded = load_rulepack(raw, source=source)
        header = loaded.document.meta
        if header.id in self._builtin_entries:
            raise RulepackValidationError("cannot overwrite built-in rulepack")
        rp_dir = self.base_dir / header.id
        rp_dir.mkdir(parents=True, exist_ok=True)
        meta_path = rp_dir / "meta.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            data = {
                "id": header.id,
                "name": header.name,
                "title": header.title,
                "description": header.description,
                "mutable": True,
                "versions": [],
            }
        next_version = max((int(v.get("version", 0)) for v in data["versions"]), default=0) + 1
        file_name = f"v{next_version}.yaml"
        target_path = rp_dir / file_name
        target_path.write_text(_dump_rulepack(loaded.content), encoding="utf-8")
        created_at = _iso_now()
        data["id"] = header.id
        data["name"] = header.name
        data["title"] = header.title
        data["description"] = header.description
        data.setdefault("versions", [])
        data["versions"].append(
            {
                "version": next_version,
                "created_at": created_at.isoformat(),
                "file": file_name,
            }
        )
        meta_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        self._cache.pop((header.id, next_version), None)
        available_versions = sorted(int(v["version"]) for v in data["versions"])
        return RulepackMeta(
            id=header.id,
            name=header.name,
            version=next_version,
            title=header.title,
            description=header.description,
            created_at=created_at,
            mutable=True,
            available_versions=available_versions,
        )

    def delete_rulepack(self, rulepack_id: str) -> None:
        if not self.allow_mutations:
            raise PermissionError("mutations disabled")
        if rulepack_id in self._builtin_entries:
            raise PermissionError("cannot delete built-in rulepack")
        rp_dir = self.base_dir / rulepack_id
        if not rp_dir.exists():
            raise KeyError(rulepack_id)
        shutil.rmtree(rp_dir)
        for key in list(self._cache):
            if key[0] == rulepack_id:
                self._cache.pop(key, None)


@lru_cache(maxsize=1)
def get_rulepack_store() -> RulepackStore:
    raw_base = os.getenv("AE_RULEPACK_DIR", "rulesets/interpret")
    base_path = Path(raw_base)
    if not base_path.is_absolute():
        base_path = Path.cwd() / base_path
    allow_mutations = os.getenv("AE_RULEPACK_ALLOW_MUTATIONS", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    builtin_dir = Path(__file__).resolve().parents[2] / "core" / "interpret_plus" / "samples"
    base_path.mkdir(parents=True, exist_ok=True)
    return RulepackStore(base_dir=base_path, builtin_dir=builtin_dir, allow_mutations=allow_mutations)


__all__ = ["RulepackStore", "get_rulepack_store"]
