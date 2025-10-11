"""Unit tests for the ephemeris pull helper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from astroengine.ephe import pull as pull_mod


def _write_kernel(path: Path, content: bytes = b"kernel") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_pull_set_copies_local_source(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    kernel = _write_kernel(source_dir / "de440s.bsp")

    result = pull_mod.pull_set(
        "de440s",
        target=tmp_path / "cache",
        source=str(source_dir),
        verify=False,
    )

    destination = result.target_dir / kernel.name
    assert destination.exists()
    assert destination.read_bytes() == kernel.read_bytes()

    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["set"] == "de440s"
    assert manifest["files"][0]["status"] == "downloaded"


def test_pull_set_skips_when_existing(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_kernel(source_dir / "de440s.bsp", b"alpha")
    target_dir = tmp_path / "cache"

    first = pull_mod.pull_set(
        "de440s",
        target=target_dir,
        source=str(source_dir),
        verify=False,
    )
    assert first.downloaded

    second = pull_mod.pull_set(
        "de440s",
        target=target_dir,
        source=str(source_dir),
        verify=False,
    )
    assert not second.downloaded
    assert second.skipped


def test_pull_set_unknown_set_raises(tmp_path: Path) -> None:
    with pytest.raises(pull_mod.PullError):
        pull_mod.pull_set("unknown", target=tmp_path / "cache", verify=False)


def test_pull_set_validates_checksums(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_dir = tmp_path / "source"
    payload = b"ephemeris"
    kernel = _write_kernel(source_dir / "kernel.bsp", payload)
    good_sha = hashlib.sha256(payload).hexdigest()

    manifest = pull_mod.EphemerisSet(
        name="testset",
        description="Test manifest",
        files=(
            pull_mod.EphemerisFile(
                filename=kernel.name,
                url="https://example.com/kernel.bsp",
                sha256=good_sha,
            ),
        ),
    )
    monkeypatch.setitem(pull_mod._EPHEMERIS_SETS, "testset", manifest)

    result = pull_mod.pull_set(
        "testset",
        target=tmp_path / "cache-good",
        source=str(source_dir),
        verify=True,
    )
    assert result.downloaded

    bad_manifest = pull_mod.EphemerisSet(
        name="badset",
        description="Bad checksum",
        files=(
            pull_mod.EphemerisFile(
                filename=kernel.name,
                url="https://example.com/kernel.bsp",
                sha256="0" * 64,
            ),
        ),
    )
    monkeypatch.setitem(pull_mod._EPHEMERIS_SETS, "badset", bad_manifest)

    with pytest.raises(pull_mod.PullError):
        pull_mod.pull_set(
            "badset",
            target=tmp_path / "cache-bad",
            source=str(source_dir),
            verify=True,
        )
