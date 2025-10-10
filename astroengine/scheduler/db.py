from __future__ import annotations

import atexit
import sqlite3
import time
from pathlib import Path
from threading import Lock

from astroengine.infrastructure.storage.sqlite import apply_default_pragmas

DB_PATH = Path("./.astroengine/queue.sqlite")

DDL = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  payload TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  state TEXT NOT NULL DEFAULT 'queued',
  dedupe_key TEXT UNIQUE,
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  run_at INTEGER,
  heartbeat_at INTEGER,
  backoff_until INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  result TEXT,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS ix_jobs_state ON jobs(state, priority, run_at);
CREATE INDEX IF NOT EXISTS ix_jobs_dedupe ON jobs(dedupe_key);
"""


_connection: sqlite3.Connection | None = None
_connection_lock = Lock()


def _close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        with _connection_lock:
            if _connection is None:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                con = sqlite3.connect(DB_PATH)
                con.row_factory = sqlite3.Row
                apply_default_pragmas(con)
                con.executescript(DDL)
                atexit.register(_close_connection)
                _connection = con
    return _connection


def connect() -> sqlite3.Connection:
    return get_connection()


def now() -> int:
    return int(time.time())
