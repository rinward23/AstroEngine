from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from .db import get_connection, now

LEASE_SEC = 120


def enqueue(
    type_: str,
    payload: dict[str, Any],
    *,
    priority: int = 100,
    run_at: int | None = None,
    dedupe_key: str | None = None,
    max_attempts: int = 5,
) -> str:
    con = get_connection()
    cur = con.cursor()
    jid = str(uuid.uuid4())
    t = now()
    try:
        cur.execute(
            """INSERT INTO jobs(id,type,payload,priority,state,dedupe_key,attempts,max_attempts,run_at,created_at,updated_at)
                 VALUES (?,?,?,?, 'queued', ?,0,?, ?,?,?)""",
            (
                jid,
                type_,
                json.dumps(payload),
                priority,
                dedupe_key,
                max_attempts,
                run_at,
                t,
                t,
            ),
        )
    except sqlite3.IntegrityError:
        if dedupe_key:
            row = cur.execute(
                "SELECT id FROM jobs WHERE dedupe_key=?", (dedupe_key,)
            ).fetchone()
            if row:
                return str(row[0])
        raise
    finally:
        con.commit()
        cur.close()
    return jid


def _recover_stale(cur: sqlite3.Cursor, t: int) -> None:
    cur.execute(
        "UPDATE jobs SET state='queued', updated_at=?, backoff_until=NULL "
        "WHERE state='running' AND (heartbeat_at IS NULL OR heartbeat_at < ?)",
        (t, t - LEASE_SEC),
    )


def claim_one() -> dict[str, Any] | None:
    con = get_connection()
    cur = con.cursor()
    t = now()

    try:
        cur.execute("BEGIN IMMEDIATE")
        _recover_stale(cur, t)

        while True:
            row = cur.execute(
                """
                SELECT * FROM jobs
                 WHERE state='queued'
                   AND (run_at IS NULL OR run_at <= ?)
                   AND (backoff_until IS NULL OR backoff_until <= ?)
                 ORDER BY priority ASC, COALESCE(run_at, 0) ASC, created_at ASC
                 LIMIT 1
                """,
                (t, t),
            ).fetchone()
            if row is None:
                con.commit()
                return None

            jid = row["id"]
            cur.execute(
                """
                UPDATE jobs
                   SET state='running',
                       attempts=attempts+1,
                       heartbeat_at=?,
                       updated_at=?
                 WHERE id=? AND state='queued'
                """,
                (t, t, jid),
            )
            if cur.rowcount:
                job_row = cur.execute(
                    "SELECT * FROM jobs WHERE id=?", (jid,)
                ).fetchone()
                con.commit()
                return dict(job_row) if job_row else None
            # Another worker claimed it; try again.
    finally:
        cur.close()


def heartbeat(job_id: str) -> None:
    con = get_connection()
    t = now()
    cur = con.cursor()
    try:
        cur.execute(
            "UPDATE jobs SET heartbeat_at=?, updated_at=? WHERE id=? AND state='running'",
            (t, t, job_id),
        )
        con.commit()
    finally:
        cur.close()


def done(job_id: str, result: dict[str, Any] | None = None) -> None:
    con = get_connection()
    t = now()
    cur = con.cursor()
    try:
        cur.execute(
            "UPDATE jobs SET state='done', result=?, updated_at=? WHERE id=?",
            (json.dumps(result or {}), t, job_id),
        )
        con.commit()
    finally:
        cur.close()


def fail(job_id: str, error: str, *, base_backoff: int = 5) -> None:
    con = get_connection()
    t = now()
    cur = con.cursor()
    try:
        row = cur.execute(
            "SELECT attempts, max_attempts FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if not row:
            return
        attempts, max_attempts = int(row[0]), int(row[1])
        if attempts >= max_attempts:
            cur.execute(
                "UPDATE jobs SET state='failed', last_error=?, updated_at=? WHERE id=?",
                (error, t, job_id),
            )
        else:
            backoff = min(300, base_backoff * (2 ** max(attempts - 1, 0)))
            cur.execute(
                "UPDATE jobs SET state='queued', backoff_until=?, last_error=?, updated_at=? WHERE id=?",
                (t + backoff, error, t, job_id),
            )
        con.commit()
    finally:
        cur.close()


def cancel(job_id: str) -> None:
    con = get_connection()
    t = now()
    cur = con.cursor()
    try:
        cur.execute(
            "UPDATE jobs SET state='canceled', updated_at=? WHERE id=? AND state IN ('queued','running')",
            (t, job_id),
        )
        con.commit()
    finally:
        cur.close()


def get(job_id: str) -> dict[str, Any] | None:
    con = get_connection()
    cur = con.cursor()
    try:
        row = cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    finally:
        cur.close()
    return dict(row) if row else None
