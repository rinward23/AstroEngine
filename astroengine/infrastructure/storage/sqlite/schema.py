"""Declarative SQLite schema used by canonical exporters."""

from __future__ import annotations

from importlib import util

_SQLALCHEMY_AVAILABLE = util.find_spec("sqlalchemy") is not None

if _SQLALCHEMY_AVAILABLE:  # pragma: no branch - exercised when dependency present
    from sqlalchemy import (
        Boolean,
        Column,
        Float,
        Index,
        Integer,
        MetaData,
        String,
        Text,
        Table,
    )

    metadata = MetaData()

    transits_events = Table(
        "transits_events",
        metadata,
        Column("ts", String, nullable=False),
        Column("moving", String, nullable=False),
        Column("target", String, nullable=False),
        Column("aspect", String, nullable=False),
        Column("orb", Float, nullable=False),
        Column("orb_abs", Float, nullable=False),
        Column("applying", Boolean, nullable=False),
        Column("score", Float, nullable=True),
        Column("profile_id", String, nullable=True),
        Column("natal_id", String, nullable=True),
        Column("event_year", Integer, nullable=False),
        Column("meta_json", Text, nullable=False, server_default="{}"),
    )

    Index("ix_transits_events_profile_ts", transits_events.c.profile_id, transits_events.c.ts)
    Index("ix_transits_events_natal_year", transits_events.c.natal_id, transits_events.c.event_year)
    Index("ix_transits_events_score", transits_events.c.score)

else:  # pragma: no cover - dependency free fallback
    metadata = None

    class _SchemaUnavailable:
        """Placeholder explaining that SQLAlchemy is required for ORM metadata."""

        def __repr__(self) -> str:
            return "<transits_events schema (SQLAlchemy not installed)>"

    transits_events = _SchemaUnavailable()

__all__ = ["metadata", "transits_events"]
