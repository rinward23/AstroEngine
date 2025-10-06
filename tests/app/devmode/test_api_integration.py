from __future__ import annotations

import importlib
import json
import textwrap
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def devmode_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("ASTROENGINE_HOME", str(home))
    monkeypatch.setenv("DEV_MODE", "1")
    monkeypatch.setenv("DEV_VALIDATE_COMMANDS", "echo ok")
    monkeypatch.setenv("DEV_PIN", "1234")

    import app.devmode.api as api_mod
    import app.devmode.backups as backups_mod
    import astroengine.infrastructure.retention as retention_mod

    importlib.reload(retention_mod)
    importlib.reload(backups_mod)
    importlib.reload(api_mod)

    app = FastAPI()
    app.include_router(api_mod.router)
    client = TestClient(app)
    client.headers.update({"X-Dev-Pin": "1234"})
    return client, tmp_path


def test_dev_apply_records_history(devmode_app):
    client, root = devmode_app
    (root / "app/devmode").mkdir(parents=True, exist_ok=True)

    diff = textwrap.dedent(
        """
        diff --git a/app/devmode/sample.txt b/app/devmode/sample.txt
        new file mode 100644
        index 0000000..e69de29
        --- /dev/null
        +++ b/app/devmode/sample.txt
        @@ -0,0 +1 @@
        +hello world
        """
    )

    payload = {
        "diff": diff,
        "message": "test patch",
        "user": "tester",
    }

    response = client.post("/v1/dev/apply", json=payload)
    assert response.status_code == 200, response.json()

    history_path = root / ".astroengine/version_history.json"
    changelog_path = root / "CHANGELOG.md"
    assert history_path.exists()
    assert changelog_path.exists()

    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history
    latest = history[-1]
    assert latest["message"] == "test patch"
    assert latest["commit"]

    changelog = changelog_path.read_text(encoding="utf-8")
    assert "test patch" in changelog


def test_backup_endpoints(devmode_app):
    client, root = devmode_app
    (root / "profiles").mkdir(parents=True, exist_ok=True)
    (root / "profiles" / "runtime.yaml").write_text("ok: 1", encoding="utf-8")

    run_resp = client.post("/v1/dev/backups/run")
    assert run_resp.status_code == 200, run_resp.text
    archive_path = Path(run_resp.json()["archive"])
    assert archive_path.exists()

    schedule_resp = client.post(
        "/v1/dev/backups/schedule", json={"interval_hours": 0}
    )
    assert schedule_resp.status_code == 200
    assert schedule_resp.json().get("status") == "canceled"

    list_resp = client.get("/v1/dev/backups")
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["backups"]

    restore_resp = client.post(
        "/v1/dev/backups/restore", json={"archive_path": str(archive_path)}
    )
    assert restore_resp.status_code == 200

    retention_resp = client.post(
        "/v1/dev/retention",
        json={"temporary_derivatives_days": 5, "run_purge": True},
    )
    assert retention_resp.status_code == 200
    assert retention_resp.json()["policy"]["temporary_derivatives_days"] == 5


def test_dev_endpoints_require_pin(devmode_app):
    client, _ = devmode_app
    client.headers.pop("X-Dev-Pin", None)

    response = client.get("/v1/dev/history")
    assert response.status_code == 403
