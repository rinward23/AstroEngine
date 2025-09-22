"""Convenience queries over the canonical SQLite exports."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .engine import ensure_sqlite_schema

__all__ = ["top_events_by_score"]


def top_events_by_score(
    db_path: str,
    *,
    limit: int = 10,
    profile_id: Optional[str] = None,
    natal_id: Optional[str] = None,
    moving: Optional[str] = None,
    target: Optional[str] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return the highest scoring transit events with optional filters."""

    import sqlite3

    ensure_sqlite_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        query = (
            "SELECT ts, moving, target, aspect, score, profile_id, natal_id, event_year, meta_json "
            "FROM transits_events"
        )
        conditions: List[str] = []
        params: List[Any] = []
        if profile_id:
            conditions.append("profile_id = ?")
            params.append(profile_id)
        if natal_id:
            conditions.append("natal_id = ?")
            params.append(natal_id)
        if moving:
            conditions.append("moving = ?")
            params.append(moving)
        if target:
            conditions.append("target = ?")
            params.append(target)
        if year is not None:
            conditions.append("event_year = ?")
            params.append(int(year))
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY score IS NULL, score DESC, ts ASC LIMIT ?"
        params.append(int(limit))
        rows = con.execute(query, params).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            payload: Dict[str, Any] = {
                "ts": row["ts"],
                "moving": row["moving"],
                "target": row["target"],
                "aspect": row["aspect"],
                "score": row["score"],
                "profile_id": row["profile_id"],
                "natal_id": row["natal_id"],
                "event_year": row["event_year"],
            }
            raw_meta = row["meta_json"]
            payload["meta"] = json.loads(raw_meta) if raw_meta else {}
            results.append(payload)
        return results
    finally:
        con.close()
