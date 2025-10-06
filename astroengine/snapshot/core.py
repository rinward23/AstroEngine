from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
import tempfile
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from fnmatch import fnmatch
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import IO

__all__ = [
    "DEFAULT_EXCLUDES",
    "SnapshotManifest",
    "VerifyReport",
    "create_snapshot",
    "verify_snapshot",
]


@dataclass
class SnapshotManifest:
    archive: str
    archive_sha256: str
    file_count: int
    bytes: int
    files: list[dict]
    meta: dict


@dataclass
class VerifyReport:
    archive: str
    ok: bool
    reason: str | None


DEFAULT_EXCLUDES = [
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
    ".venv",
    "*.pyc",
    "*.parquet",
    "*.sqlite",
    "*.db",
    "*.ics",
    "out/",
    "dist/",
    "build/",
]

MANIFEST_NAME = "SNAPSHOT.MF.json"
_BUFFER_SIZE = 1024 * 1024


def _tool_version() -> str:
    try:
        return version("astroengine")
    except PackageNotFoundError:
        return "0"


def _is_excluded(path: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if normalized.endswith("/"):
            prefix = normalized.rstrip("/")
            if path == prefix or path.startswith(prefix + "/"):
                return True
        if fnmatch(path, normalized):
            return True
    return False


def _walk_source(
    source: Path,
    rel: PurePosixPath,
    excludes: Sequence[str],
    directories: set[str],
    files: list[tuple[Path, str]],
) -> None:
    rel_posix = rel.as_posix()
    if _is_excluded(rel_posix, excludes):
        return
    if source.is_dir():
        directories.add(rel_posix)
        children = sorted(source.iterdir(), key=lambda p: p.name)
        for child in children:
            child_rel = rel / child.name
            _walk_source(child, PurePosixPath(child_rel.as_posix()), excludes, directories, files)
    elif source.is_file():
        files.append((source, rel_posix))


@dataclass
class _PreparedFile:
    arcname: str
    size: int
    sha256: str
    spool: IO[bytes]


def _prepare_files(
    files: list[tuple[Path, str]],
    stack: ExitStack,
) -> tuple[list[_PreparedFile], list[dict], int]:
    prepared: list[_PreparedFile] = []
    manifest_entries: list[dict] = []
    total_size = 0
    for filesystem_path, arcname in sorted(files, key=lambda item: item[1]):
        spool = stack.enter_context(tempfile.SpooledTemporaryFile(max_size=_BUFFER_SIZE))
        digest = hashlib.sha256()
        size = 0
        with filesystem_path.open("rb") as handle:
            while True:
                chunk = handle.read(_BUFFER_SIZE)
                if not chunk:
                    break
                spool.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        spool.seek(0)
        manifest_entries.append({
            "path": arcname,
            "sha256": digest.hexdigest(),
            "size": size,
        })
        prepared.append(_PreparedFile(arcname=arcname, size=size, sha256=digest.hexdigest(), spool=spool))
        total_size += size
    return prepared, manifest_entries, total_size


def create_snapshot(
    sources: Sequence[str],
    out_path: str,
    *,
    exclude_globs: Sequence[str] | None = None,
    meta: dict | None = None,
) -> SnapshotManifest:
    if not sources:
        raise ValueError("at least one source path is required")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    excludes: list[str] = list(DEFAULT_EXCLUDES)
    if exclude_globs:
        excludes.extend(exclude_globs)

    directories: set[str] = set()
    files: list[tuple[Path, str]] = []
    resolved_sources: list[tuple[Path, PurePosixPath]] = []
    seen_roots: set[str] = set()
    seen_paths: set[str] = set()

    for src in sorted({str(Path(p)) for p in sources}):
        source_path = Path(src).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"source path does not exist: {source_path}")

        resolved_key = str(source_path)
        if resolved_key in seen_paths:
            raise ValueError(f"duplicate source path provided: {source_path}")
        seen_paths.add(resolved_key)

        rel = PurePosixPath(source_path.name)
        rel_key = rel.as_posix()
        if rel_key in seen_roots:
            label = rel_key or str(source_path)
            raise ValueError(f"duplicate archive root name detected: {label}")
        seen_roots.add(rel_key)

        resolved_sources.append((source_path, rel))

    for source_path, rel in resolved_sources:
        _walk_source(source_path, rel, excludes, directories, files)

    seen_arcnames: set[str] = set()
    for _, arcname in files:
        if arcname == MANIFEST_NAME:
            raise ValueError(f"source set includes reserved manifest name: {MANIFEST_NAME}")
        if arcname in seen_arcnames:
            raise ValueError(f"duplicate archive member path produced: {arcname}")
        seen_arcnames.add(arcname)

    directories = set(dir_path for dir_path in directories if dir_path)

    manifest_meta = dict(meta or {})
    manifest_meta.setdefault("tool", {"name": "astroengine.snapshot", "version": _tool_version()})

    with ExitStack() as stack:
        prepared_files, manifest_entries, total_size = _prepare_files(files, stack)
        manifest_entries.sort(key=lambda item: item["path"])
        manifest_payload = {
            "archive": str(target),
            "file_count": len(manifest_entries),
            "bytes": total_size,
            "files": manifest_entries,
            "meta": manifest_meta,
        }
        manifest_bytes = json.dumps(
            manifest_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        with open(target, "wb") as file_handle:
            with gzip.GzipFile(fileobj=file_handle, mode="wb", compresslevel=9, mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    manifest_info = tarfile.TarInfo(MANIFEST_NAME)
                    manifest_info.size = len(manifest_bytes)
                    manifest_info.mtime = 0
                    manifest_info.mode = 0o644
                    manifest_info.uid = manifest_info.gid = 0
                    manifest_info.uname = manifest_info.gname = ""
                    tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

                    for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
                        name = directory if directory.endswith("/") else f"{directory}/"
                        info = tarfile.TarInfo(name)
                        info.type = tarfile.DIRTYPE
                        info.mtime = 0
                        info.mode = 0o755
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        tar.addfile(info)

                    for prepared in prepared_files:
                        info = tarfile.TarInfo(prepared.arcname)
                        info.size = prepared.size
                        info.mtime = 0
                        info.mode = 0o644
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        prepared.spool.seek(0)
                        tar.addfile(info, prepared.spool)

    archive_hash = hashlib.sha256()
    with open(target, "rb") as handle:
        for chunk in iter(lambda: handle.read(_BUFFER_SIZE), b""):
            archive_hash.update(chunk)

    return SnapshotManifest(
        archive=str(target),
        archive_sha256=archive_hash.hexdigest(),
        file_count=len(manifest_entries),
        bytes=total_size,
        files=manifest_entries,
        meta=manifest_meta,
    )


def verify_snapshot(archive_path: str) -> VerifyReport:
    archive = Path(archive_path)
    if not archive.exists():
        return VerifyReport(archive=str(archive), ok=False, reason="archive not found")

    try:
        tar = tarfile.open(archive, mode="r:gz")
    except tarfile.TarError as exc:  # pragma: no cover - defensive
        return VerifyReport(archive=str(archive), ok=False, reason=f"unable to open archive: {exc}")

    with tar:
        try:
            manifest_member = tar.getmember(MANIFEST_NAME)
        except KeyError:
            return VerifyReport(archive=str(archive), ok=False, reason="manifest missing")

        manifest_file = tar.extractfile(manifest_member)
        if manifest_file is None:
            return VerifyReport(archive=str(archive), ok=False, reason="manifest unreadable")
        with manifest_file:
            try:
                manifest_data = json.load(manifest_file)
            except json.JSONDecodeError as exc:
                return VerifyReport(
                    archive=str(archive),
                    ok=False,
                    reason=f"manifest invalid JSON: {exc}",
                )

        files = manifest_data.get("files", [])
        expected_count = int(manifest_data.get("file_count", len(files)))
        expected_bytes = int(manifest_data.get("bytes", 0))

        actual_files = {
            member.name: member
            for member in tar.getmembers()
            if member.isfile() and member.name != MANIFEST_NAME
        }

        if len(files) != expected_count:
            return VerifyReport(
                archive=str(archive), ok=False, reason="manifest file_count mismatch"
            )

        if set(actual_files) != {entry.get("path") for entry in files}:
            return VerifyReport(
                archive=str(archive), ok=False, reason="archive contents differ from manifest"
            )

        total_bytes = 0
        for entry in files:
            path = entry.get("path")
            if path is None or path not in actual_files:
                return VerifyReport(
                    archive=str(archive), ok=False, reason=f"missing entry: {path}"
                )
            member = actual_files[path]
            extracted = tar.extractfile(member)
            if extracted is None:
                return VerifyReport(
                    archive=str(archive), ok=False, reason=f"unreadable entry: {path}"
                )
            digest = hashlib.sha256()
            size = 0
            with extracted:
                for chunk in iter(lambda: extracted.read(_BUFFER_SIZE), b""):
                    digest.update(chunk)
                    size += len(chunk)
            if size != member.size or size != int(entry.get("size", -1)):
                return VerifyReport(
                    archive=str(archive), ok=False, reason=f"size mismatch: {path}"
                )
            if digest.hexdigest() != entry.get("sha256"):
                return VerifyReport(
                    archive=str(archive), ok=False, reason=f"sha256 mismatch: {path}"
                )
            total_bytes += size

        if total_bytes != expected_bytes:
            return VerifyReport(
                archive=str(archive), ok=False, reason="total byte count mismatch"
            )

    return VerifyReport(archive=str(archive), ok=True, reason=None)
