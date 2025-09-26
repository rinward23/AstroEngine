from __future__ import annotations

import importlib
import json

import pytest


@pytest.fixture(autouse=True)
def scheduler_test_db(monkeypatch, tmp_path):
    import astroengine.scheduler.db as db_module
    importlib.reload(db_module)
    db_path = tmp_path / "queue.sqlite"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    import astroengine.scheduler.queue as queue_module
    importlib.reload(queue_module)

    import astroengine.scheduler.worker as worker_module
    importlib.reload(worker_module)

    yield


def test_worker_processes_progressions(monkeypatch):
    from astroengine.scheduler import queue, worker

    captured: list[dict[str, object]] = []

    def fake_progressions(payload: dict[str, object]) -> list[int]:
        captured.append(payload)
        return [1, 2, 3]

    monkeypatch.setitem(worker.HANDLERS, "scan:progressions", fake_progressions)

    jid = queue.enqueue("scan:progressions", {"payload": "data"})
    worker.run_worker(sleep_sec=0.0, heartbeat_sec=0.0, max_iterations=5)

    job = queue.get(jid)
    assert job is not None
    assert job["state"] == "done"
    summary = json.loads(job["result"])
    assert summary == {"summary": {"count": 3}}
    assert captured and captured[0]["payload"] == "data"
