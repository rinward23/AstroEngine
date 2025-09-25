"""Declarative SQLite schema used by canonical exporters."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
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

Index(
    "ix_transits_events_profile_ts", transits_events.c.profile_id, transits_events.c.ts
)
Index(
    "ix_transits_events_natal_year",
    transits_events.c.natal_id,
    transits_events.c.event_year,
)
Index("ix_transits_events_score", transits_events.c.score)

__all__ = ["metadata", "transits_events"]
