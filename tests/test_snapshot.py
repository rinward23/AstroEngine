from pathlib import Path

import pytest

from astroengine.snapshot.core import create_snapshot, verify_snapshot


def test_deterministic(tmp_path: Path) -> None:
    d = tmp_path / "proj"
    d.mkdir()
    (d / "a.txt").write_text("hello\n")
    (d / "b").mkdir()
    (d / "b" / "b.txt").write_text("world\n")
    out = tmp_path / "snap.tar.gz"
    m1 = create_snapshot([str(d)], str(out))
    h1 = m1.archive_sha256
    (d / "a.txt").touch()
    m2 = create_snapshot([str(d)], str(out))
    h2 = m2.archive_sha256
    assert h1 == h2
    vr = verify_snapshot(str(out))
    assert vr.ok


def test_excludes(tmp_path: Path) -> None:
    d = tmp_path / "proj"
    d.mkdir()
    (d / ".git").mkdir()
    (d / "x.pyc").write_text("1")
    (d / "keep.txt").write_text("ok")
    out = tmp_path / "snap.tar.gz"
    rep = create_snapshot([str(d)], str(out))
    paths = [f["path"] for f in rep.files]
    assert "keep.txt" in "/".join(paths)
    assert not any(p.endswith(".pyc") or p.startswith(".git/") for p in paths)


def test_duplicate_roots_disallowed(tmp_path: Path) -> None:
    left = tmp_path / "proj"
    right_root = tmp_path / "else"
    left.mkdir()
    right_root.mkdir()
    right = right_root / "proj"
    right.mkdir()
    (left / "a.txt").write_text("1")
    (right / "b.txt").write_text("2")
    out = tmp_path / "snap.tar.gz"
    with pytest.raises(ValueError):
        create_snapshot([str(left), str(right)], str(out))
