from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Integer, Float, Boolean, Enum, JSON, ForeignKey, DateTime, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

# --- Enums -----------------------------------------------------------------
class ChartKind(str, enum.Enum):
    natal = "natal"
    solar_return = "solar_return"
    lunar_return = "lunar_return"
    planetary_return = "planetary_return"
    progression_secondary = "progression_secondary"
    solar_arc = "solar_arc"
    composite_midpoint = "composite_midpoint"
    davison = "davison"
    transit = "transit"

class EventType(str, enum.Enum):
    aspect = "aspect"
    return_event = "return"
    voc_moon = "voc_moon"
    solar_phase = "solar_phase"  # combust / under_beams / cazimi
    electional_window = "electional_window"
    custom = "custom"

class ExportType(str, enum.Enum):
    ics = "ics"
    pdf = "pdf"
    md = "md"

class ExportStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"

# --- Models ----------------------------------------------------------------
class OrbPolicy(Base):
    __tablename__ = "orb_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    # e.g., {"Sun": 8.0, "Moon": 6.0}
    per_object: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    # e.g., {"conjunction": 8.0, "sextile": 3.0}
    per_aspect: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    # e.g., rules like {"luminaries_tighter": true, "outers_wider": true}
    adaptive_rules: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SeverityProfile(Base):
    __tablename__ = "severity_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # weights: {"conjunction": 1.0, "square": 1.2, ...}
    weights: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    # modifiers: {"dignity": {...}, "house": {...}}
    modifiers: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Chart(Base):
    __tablename__ = "charts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[ChartKind] = mapped_column(Enum(ChartKind), nullable=False)

    dt_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tzid: Mapped[Optional[str]] = mapped_column(String(64))

    # Location
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    alt_m: Mapped[Optional[float]] = mapped_column(Float)
    location_name: Mapped[Optional[str]] = mapped_column(String(160))

    # Houses & positions
    house_system: Mapped[Optional[str]] = mapped_column(String(16))
    houses: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # cusps etc.
    positions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # body → lon/lat/speed

    source: Mapped[Optional[str]] = mapped_column(String(64))  # e.g., "user", "computed"

    events: Mapped[List["Event"]] = relationship(back_populates="chart", cascade="all, delete-orphan")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

Index("ix_charts_dt", Chart.dt_utc)

class RuleSetVersion(Base):
    __tablename__ = "ruleset_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g., "electional_default"
    version: Mapped[int] = mapped_column(Integer, default=1)
    definition_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[Optional[str]] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

Index("uq_ruleset_key_version", RuleSetVersion.key, RuleSetVersion.version, unique=True)

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)

    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    objects: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # e.g., {"A":"Mars","B":"Venus","aspect":"sextile"}

    score: Mapped[Optional[float]] = mapped_column(Float)
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    tags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # arbitrary labels

    chart_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("charts.id"))
    chart: Mapped[Optional[Chart]] = relationship(back_populates="events")

    ruleset_version_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ruleset_versions.id"))
    severity_profile_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("severity_profiles.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

Index("ix_events_start", Event.start_ts)
Index("ix_events_type_start", Event.type, Event.start_ts)

class AsteroidMeta(Base):
    __tablename__ = "asteroid_meta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mpc_number: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120), index=True)
    designation: Mapped[Optional[str]] = mapped_column(String(120))
    body_type: Mapped[Optional[str]] = mapped_column(String(40))  # e.g., asteroid, tno, centaur
    is_user_defined: Mapped[bool] = mapped_column(Boolean, default=False)
    default_orb: Mapped[Optional[float]] = mapped_column(Float)
    keywords: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

Index("uq_asteroid_unique", AsteroidMeta.name, AsteroidMeta.designation, unique=True)

class ExportJob(Base):
    __tablename__ = "export_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ExportType] = mapped_column(Enum(ExportType), nullable=False)
    status: Mapped[ExportStatus] = mapped_column(Enum(ExportStatus), default=ExportStatus.pending)
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    file_ref: Mapped[Optional[str]] = mapped_column(String(255))  # path or object store key

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# convenience exports
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
    "ExportStatus",
]
