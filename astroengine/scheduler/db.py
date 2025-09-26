from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("./.astroengine/queue.sqlite")

DDL = """
PRAGMA journal_mode=WAL;
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


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    return con


def now() -> int:
    return int(time.time())
