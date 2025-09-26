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


def test_enqueue_and_dedupe():
    from astroengine.scheduler import queue

    jid1 = queue.enqueue("scan:test", {"payload": 1}, dedupe_key="same")
    jid2 = queue.enqueue("scan:test", {"payload": 1}, dedupe_key="same")
    assert jid1 == jid2

    job = queue.get(jid1)
    assert job is not None
    assert job["state"] == "queued"


def test_claim_heartbeat_done():
    from astroengine.scheduler import queue

    jid = queue.enqueue("scan:test", {"payload": 2})
    job = queue.claim_one()
    assert job is not None
    assert job["id"] == jid
    assert job["state"] == "running"

    first_hb = job["heartbeat_at"]
    queue.heartbeat(jid)
    refreshed = queue.get(jid)
    assert refreshed is not None
    assert refreshed["heartbeat_at"] >= first_hb

    queue.done(jid, {"ok": True})
    done_job = queue.get(jid)
    assert done_job is not None
    assert done_job["state"] == "done"
    assert json.loads(done_job["result"]) == {"ok": True}


def test_fail_backoff_and_max_attempts(monkeypatch):
    from astroengine.scheduler import queue

    jid = queue.enqueue("scan:test", {"payload": 3}, max_attempts=2)
    job = queue.claim_one()
    assert job is not None
    assert job["attempts"] == 1

    queue.fail(jid, "first error", base_backoff=2)
    queued = queue.get(jid)
    assert queued is not None
    assert queued["state"] == "queued"
    assert queued["attempts"] == 1
    assert queued["backoff_until"] >= queued["updated_at"]

    assert queue.claim_one() is None

    original_now = queue.now
    monkeypatch.setattr(queue, "now", lambda: original_now() + 10)
    try:
        job_retry = queue.claim_one()
    finally:
        monkeypatch.setattr(queue, "now", original_now)
    assert job_retry is not None
    assert job_retry["attempts"] == 2

    queue.fail(jid, "second error", base_backoff=2)
    failed = queue.get(jid)
    assert failed is not None
    assert failed["state"] == "failed"
    assert "second error" in failed["last_error"]
