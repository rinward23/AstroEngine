
"""ORM models used by the AstroEngine service stack."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChartKind(str, enum.Enum):
    """Enumerates chart categories supported by the persistence layer."""

    natal = "natal"
    transit = "transit"
    progressed = "progressed"


class EventType(str, enum.Enum):
    """Enumerates event records stored against charts."""

    custom = "custom"
    transit = "transit"
    progression = "progression"


class ExportType(str, enum.Enum):
    """Enumerates supported export job formats."""

    ics = "ics"
    csv = "csv"
    json = "json"


class OrbPolicy(Base):
    """Configurable orb policy definitions."""

    __tablename__ = "orb_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    per_object: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SeverityProfile(Base):
    """Profile definitions for severity computation."""

    __tablename__ = "severity_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    weights: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Chart(Base):
    """Represents a persisted chart instance."""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[ChartKind] = mapped_column(Enum(ChartKind), nullable=False)
    dt_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="chart",
        cascade="all, delete-orphan",
    )


class Event(Base):
    """Event entries that can be attached to charts."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"))
    objects: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    chart: Mapped[Chart] = relationship("Chart", back_populates="events")


class RuleSetVersion(Base):
    """Versioned rule set definitions."""

    __tablename__ = "ruleset_versions"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_ruleset_key_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AsteroidMeta(Base):
    """Metadata for tracked asteroids and minor planets."""

    __tablename__ = "asteroid_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)


class ExportJob(Base):
    """Queued export jobs maintained by the application."""

    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ExportType] = mapped_column(Enum(ExportType), nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)



__all__ = [
    "OrbPolicy",
    "SeverityProfile",
    "Chart",
    "Event",
    "RuleSetVersion",
    "AsteroidMeta",
    "ExportJob",
    "ChartKind",
    "EventType",
    "ExportType",

]
