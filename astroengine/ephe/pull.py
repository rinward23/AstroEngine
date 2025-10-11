"""Utilities for downloading ephemeris datasets."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_CACHE_ROOT = Path(
    os.environ.get("ASTROENGINE_CACHE", str(Path.home() / ".skyfield"))
).expanduser()


@dataclass(frozen=True)
class EphemerisFile:
    """Metadata describing a single ephemeris asset."""

    filename: str
    url: str
    sha256: str | None = None


@dataclass(frozen=True)
class EphemerisSet:
    """Manifest describing a named ephemeris bundle."""

    name: str
    description: str
    files: Sequence[EphemerisFile]

    def default_target(self) -> Path:
        base = DEFAULT_CACHE_ROOT
        default_root = Path.home() / ".skyfield"
        if base == default_root:
            return base
        return base / "skyfield" / self.name


@dataclass
class PullResult:
    """Outcome of a pull operation."""

    set_name: str
    target_dir: Path
    downloaded: list[Path]
    skipped: list[Path]
    manifest_path: Path


class PullError(RuntimeError):
    """Raised when an ephemeris pull operation fails."""


_EPHEMERIS_SETS: dict[str, EphemerisSet] = {
    "de440s": EphemerisSet(
        name="de440s",
        description="JPL DE440s planetary ephemeris (short-span kernel).",
        files=(
            EphemerisFile(
                filename="de440s.bsp",
                url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp",
                sha256=None,
            ),
        ),
    ),
}


def available_sets() -> list[str]:
    """Return the list of known ephemeris set identifiers."""

    return sorted(_EPHEMERIS_SETS)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _hash_stream(stream: Iterator[bytes], dest: Path) -> str:
    digest = hashlib.sha256()
    dest_tmp = dest.with_suffix(dest.suffix + ".part")
    with dest_tmp.open("wb") as handle:
        for chunk in stream:
            if not chunk:
                continue
            handle.write(chunk)
            digest.update(chunk)
    dest_tmp.replace(dest)
    return digest.hexdigest()


def _copy_local(source: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as src, dest.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _download_http(url: str, dest: Path, *, timeout: int) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, stream=True, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        raise PullError(f"Failed to fetch {url}: {exc}") from exc

    with response:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - HTTP error path
            raise PullError(f"Download failed with status {response.status_code}") from exc
        return _hash_stream(response.iter_content(64 * 1024), dest)


def _resolve_source(spec: EphemerisFile, source: str | None) -> tuple[str | None, Path | None]:
    if not source:
        return spec.url, None
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        base = source.rstrip("/") + "/"
        return urljoin(base, spec.filename), None
    if parsed.scheme == "file":
        local = Path(parsed.path)
        if local.is_dir():
            return None, (local / spec.filename)
        return None, local
    local_path = Path(source)
    if local_path.is_dir():
        return None, local_path / spec.filename
    return None, local_path


def pull_set(
    set_name: str,
    *,
    target: Path | None = None,
    source: str | None = None,
    force: bool = False,
    timeout: int = 60,
    verify: bool = True,
) -> PullResult:
    """Download (or copy) an ephemeris set into *target*."""

    try:
        manifest = _EPHEMERIS_SETS[set_name]
    except KeyError as exc:
        available = ", ".join(sorted(_EPHEMERIS_SETS))
        raise PullError(f"Unknown ephemeris set '{set_name}'. Available: {available}.") from exc

    target_root = Path(target) if target is not None else manifest.default_target()
    target_root = target_root.expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    skipped: list[Path] = []
    manifest_records: list[dict[str, object]] = []

    for file_spec in manifest.files:
        destination = target_root / file_spec.filename
        resolved_url, local_source = _resolve_source(file_spec, source)

        if destination.exists() and not force:
            existing_digest = _hash_file(destination) if verify or file_spec.sha256 else None
            if verify and file_spec.sha256 and existing_digest != file_spec.sha256:
                raise PullError(
                    f"Checksum mismatch for {destination}; expected {file_spec.sha256}, found {existing_digest}."
                )
            skipped.append(destination)
            manifest_records.append(
                {
                    "filename": file_spec.filename,
                    "status": "skipped",
                    "path": str(destination),
                    "source": source or file_spec.url,
                    "sha256": existing_digest,
                }
            )
            continue

        if local_source is not None:
            if not local_source.exists():
                raise PullError(f"Local source {local_source} does not exist")
            digest = _copy_local(local_source, destination)
        else:
            if resolved_url is None:
                raise PullError("No valid source resolved for download")
            digest = _download_http(resolved_url, destination, timeout=timeout)

        if verify and file_spec.sha256 and digest != file_spec.sha256:
            destination.unlink(missing_ok=True)
            raise PullError(
                f"Checksum mismatch for {file_spec.filename}; expected {file_spec.sha256}, found {digest}."
            )

        downloaded.append(destination)
        manifest_records.append(
            {
                "filename": file_spec.filename,
                "status": "downloaded",
                "path": str(destination),
                "source": resolved_url if resolved_url is not None else str(local_source),
                "sha256": digest,
            }
        )

    manifest_payload = {
        "set": set_name,
        "description": manifest.description,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": str(target_root),
        "files": manifest_records,
    }
    manifest_path = target_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return PullResult(
        set_name=set_name,
        target_dir=target_root,
        downloaded=downloaded,
        skipped=skipped,
        manifest_path=manifest_path,
    )


__all__ = [
    "available_sets",
    "pull_set",
    "PullError",
    "PullResult",
    "EphemerisSet",
    "EphemerisFile",
]
