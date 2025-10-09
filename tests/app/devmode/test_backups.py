from __future__ import annotations

import importlib
import json
import os
import time
import zipfile
from pathlib import Path

import pytest


@pytest.fixture()
def devmode_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("ASTROENGINE_HOME", str(home))
    monkeypatch.setenv("DEV_MODE", "1")
    yield tmp_path


def _reload_modules():
    import app.devmode.backups as backups_mod
    import astroengine.infrastructure.retention as retention_mod

    importlib.reload(retention_mod)
    importlib.reload(backups_mod)
    return backups_mod, retention_mod


def test_create_and_restore_backup(devmode_env):
    root = devmode_env
    home = Path(os.environ["ASTROENGINE_HOME"])
    backups, _ = _reload_modules()

    (root / "profiles").mkdir(parents=True)
    (root / "astroengine/config").mkdir(parents=True)
    (root / "astroengine/chart").mkdir(parents=True)
    (root / "astroengine/profiles").mkdir(parents=True)
    (home / "natals").mkdir(parents=True, exist_ok=True)

    (root / "profiles" / "default.yaml").write_text("profile: default", encoding="utf-8")
    (root / "astroengine/config" / "settings.json").write_text(
        json.dumps({"k": "v"}), encoding="utf-8"
    )
    (root / "astroengine/chart" / "template.txt").write_text("chart", encoding="utf-8")
    (home / "natals" / "user.json").write_text("{}", encoding="utf-8")

    archive = backups.create_backup_zip(root, timestamp=1_700_000_000)
    assert archive.exists()

    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
    assert "profiles/default.yaml" in names
    assert "astroengine/config/settings.json" in names
    assert ".astroengine/natals/user.json" in names

    # Remove files and restore from archive
    for path in [
        root / "profiles" / "default.yaml",
        root / "astroengine/config" / "settings.json",
        root / "astroengine/chart" / "template.txt",
        home / "natals" / "user.json",
    ]:
        path.unlink()

    restored = backups.restore_backup_zip(archive, root)
    assert any("default.yaml" in r for r in restored)
    assert (root / "profiles" / "default.yaml").exists()
    assert (home / "natals" / "user.json").exists()


def test_schedule_and_run_backup_job(devmode_env):
    root = devmode_env
    backups, retention_mod = _reload_modules()

    (root / "profiles").mkdir()
    (root / "profiles" / "snap.txt").write_text("data", encoding="utf-8")

    retention_mod.save_policy({"temporary_derivatives_days": 7})
    derivatives = Path(os.environ["ASTROENGINE_HOME"]) / "derivatives"
    derivatives.mkdir(parents=True, exist_ok=True)
    old_file = derivatives / "old.txt"
    old_file.write_text("old", encoding="utf-8")
    old_age = time.time() - (10 * 86400)
    os.utime(old_file, (old_age, old_age))

    schedule = backups.schedule_backups(interval_hours=1, root=root, now_ts=1_000_000)
    job_id = schedule.get("job_id")
    assert job_id

    result = backups.run_backup_job({"root": str(root)})
    assert Path(result["archive"]).exists()
    assert result["retention"]["deleted"] >= 1
    assert not old_file.exists()

    updated_schedule = backups.load_schedule()
    assert "last_backup" in updated_schedule
    assert updated_schedule.get("job_id")


def test_retention_module_purge(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("ASTROENGINE_HOME", str(home))

    import astroengine.infrastructure.retention as retention_mod

    importlib.reload(retention_mod)

    policy = {"temporary_derivatives_days": 3}
    retention_mod.save_policy(policy)
    root = home / "derivatives"
    root.mkdir(parents=True, exist_ok=True)
    old_file = root / "old.bin"
    new_file = root / "new.bin"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    reference = 2_000_000
    old_age = reference - (5 * 86400)
    new_age = reference - (1 * 86400)
    os.utime(old_file, (old_age, old_age))
    os.utime(new_file, (new_age, new_age))

    preview = retention_mod.purge_temporary_derivatives(now=reference, dry_run=True)
    assert preview["eligible"] == 1
    assert old_file.exists()

    result = retention_mod.purge_temporary_derivatives(now=reference)
    assert result["deleted"] == 1
    assert not old_file.exists()
    assert new_file.exists()
