
"""SQLAlchemy models backing the AstroEngine Plus API.

This module defines a compact set of persistence primitives that power the
Plus routers and repositories used throughout the test-suite.  The goal is to
provide ergonomic model constructors that mirror the lightweight repositories
used in tests while keeping the schema aligned with the module → submodule →
channel → subchannel hierarchy enforced elsewhere in the project.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Enum as SAEnum,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy.sql import func

from .base import Base


def _table_args(*constraints: Any) -> tuple[Any, ...]:
    """Return ``__table_args__`` with SQLite autoincrement enabled."""

    return (*constraints, {"sqlite_autoincrement": True, "extend_existing": True})


def _coerce_version_value(value: Any) -> str:
    """Normalise version values supplied as tuples, lists, or numbers."""

    if isinstance(value, (tuple, list)):
        return ".".join(str(part) for part in value)
    return str(value)



def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _uuid_hex() -> str:
    """Return a random UUID4 hex string."""

    return uuid4().hex


class ChartKind(str, enum.Enum):
    """Enumeration of supported chart archetypes."""

    natal = "natal"
    transit = "transit"
    synastry = "synastry"
    composite = "composite"
    progressed = "progressed"
    solar_arc = "solar_arc"
    solar_return = "solar_return"
    lunar_return = "lunar_return"
    custom = "custom"


class EventType(str, enum.Enum):
    """Enumeration of supported event types."""

    transit = "transit"
    return_ = "return"
    progression = "progression"
    solar_arc = "solar_arc"
    custom = "custom"


class ExportType(str, enum.Enum):
    """Enumeration of supported export job types."""

    ics = "ics"
    csv = "csv"
    json = "json"
    webhook = "webhook"



class TimestampMixin:
    """Adds creation and update timestamps to persisted records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ModuleScopeMixin:
    """Record the module → channel scope associated with stored entities."""

    module: Mapped[str] = mapped_column(
        String(64), nullable=False, default="plus", server_default=text("'plus'")
    )
    submodule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(64), nullable=False, default="transits", server_default=text("'transits'")
    )
    subchannel: Mapped[str | None] = mapped_column(String(64), nullable=True)



class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Aggregate orb policy definitions exposed via the Plus API."""

    __tablename__ = "orb_policies"
    __table_args__ = _table_args(
        UniqueConstraint("name", name="uq_orb_policy_name"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "name",
            name="uq_orb_policies_scope_name",
        ),
        Index("ix_orb_policies_module_channel", "module", "channel"),
        Index(
            "ix_orb_policies_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_orb_policies_created_at", "created_at"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_object: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    per_aspect: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    adaptive_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    body: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aspect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    orb_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)

    profile_key = synonym("name")

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        body = kwargs.pop("body", None)
        aspect = kwargs.pop("aspect", None)
        orb_degrees = kwargs.pop("orb_degrees", None)


        if profile_key is not None:
            kwargs.setdefault("name", str(profile_key))
            kwargs.setdefault("module", str(profile_key))

        per_object = kwargs.pop("per_object", None)
        per_aspect = kwargs.pop("per_aspect", None)

        if body is not None and orb_degrees is not None:
            per_object = {str(body): float(orb_degrees)}
        elif per_object is None:
            per_object = {}

        if aspect is not None and orb_degrees is not None:
            per_aspect = {str(aspect).lower(): float(orb_degrees)}
        elif per_aspect is None:
            per_aspect = {}

        kwargs.setdefault("per_object", per_object)
        kwargs.setdefault("per_aspect", per_aspect)
        kwargs.setdefault("adaptive_rules", {})

        if "name" not in kwargs:
            tokens = [profile_key or "policy", body or "object", aspect or "aspect"]
            kwargs["name"] = ":".join(str(token) for token in tokens)

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = str(profile_key)



class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Store severity weights used during scoring routines."""

    __tablename__ = "severity_profiles"
    __table_args__ = _table_args(
        Index(
            "ix_severity_profiles_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_severity_profiles_created_at", "created_at"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class TraditionalRun(ModuleScopeMixin, TimestampMixin, Base):
    """Persisted payloads for traditional engine runs."""

    __tablename__ = "traditional_runs"
    __table_args__ = _table_args(
        Index("ix_traditional_runs_kind", "kind"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "run_id",
            name="uq_traditional_runs_scope_run_id",
        ),
        Index(
            "ix_traditional_runs_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_traditional_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, default=_uuid_hex)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile_key = synonym("name")

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        weights = kwargs.pop("weights", None)
        modifiers = kwargs.pop("modifiers", None)
        if profile_key is not None:

            kwargs.setdefault("name", str(profile_key))

        kwargs.setdefault("weights", weights or {})
        if modifiers is not None:
            kwargs.setdefault("modifiers", modifiers)

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = str(profile_key)


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualise detected events."""


    __tablename__ = "charts"
    __table_args__ = _table_args(
        UniqueConstraint("chart_key", name="uq_charts_chart_key"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "chart_key",
            name="uq_charts_scope_key",
        ),
        Index(
            "ix_charts_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_charts_dt_utc", "dt_utc"),
        Index("ix_charts_created_at", "created_at"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ChartKind.natal.value, server_default=text("'natal'")

    )
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    _dt_utc: Mapped[datetime | None] = mapped_column(
        "dt_utc", DateTime(timezone=True), nullable=True
    )

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )


    def __init__(self, **kwargs: Any) -> None:

        dt_utc = kwargs.pop("dt_utc", None)
        kind = kwargs.pop("kind", None)
        chart_key = kwargs.pop("chart_key", None)
        profile_key = kwargs.pop("profile_key", None)

        if dt_utc is not None:
            kwargs.setdefault("_dt_utc", _ensure_utc(dt_utc))

        if kind is not None:
            if isinstance(kind, ChartKind):
                kwargs.setdefault("kind", kind.value)
            else:
                kwargs.setdefault("kind", str(kind))

        kwargs.setdefault("chart_key", str(chart_key or uuid4().hex))
        kwargs.setdefault("profile_key", str(profile_key or "default"))

        data = kwargs.pop("data", None)
        kwargs.setdefault("data", data or {})

        super().__init__(**kwargs)

    @property
    def dt_utc(self) -> datetime | None:
        return self._dt_utc

    @dt_utc.setter
    def dt_utc(self, value: datetime | None) -> None:
        self._dt_utc = _ensure_utc(value) if value is not None else None


class RulesetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rule bundles consumed by scans and exports."""

    __tablename__ = "ruleset_versions"

    __table_args__ = _table_args(
        UniqueConstraint("ruleset_key", "version", name="uq_ruleset_version"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "ruleset_key",
            "version",
            name="uq_ruleset_versions_scope_key_version",
        ),
        Index("ix_ruleset_versions_module_channel", "module", "channel"),
        Index(
            "ix_ruleset_versions_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_ruleset_versions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ruleset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    key = synonym("ruleset_key")

    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")

    def __init__(self, **kwargs: Any) -> None:
        ruleset_key = kwargs.pop("ruleset_key", None)
        version_value = kwargs.pop("version", None)
        definition = kwargs.pop("definition", None)
        checksum = kwargs.pop("checksum", None)

        if ruleset_key is not None:
            kwargs.setdefault("ruleset_key", str(ruleset_key))


        if version_value is not None:
            kwargs.setdefault("version", _coerce_version_value(version_value))


        if definition is not None:
            kwargs.setdefault("definition", definition)
        else:
            kwargs.setdefault("definition", {})

        if checksum is not None:
            kwargs.setdefault("checksum", str(checksum))
        else:
            kwargs.setdefault("checksum", uuid4().hex)

        super().__init__(**kwargs)

    @property
    def key(self) -> str:
        return self.ruleset_key

    @key.setter
    def key(self, value: str) -> None:
        self.ruleset_key = value


class Event(ModuleScopeMixin, TimestampMixin, Base):
    """Detected events referencing source charts and rulesets."""

    __tablename__ = "events"

    __table_args__ = _table_args(
        UniqueConstraint("event_key", name="uq_events_event_key"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "event_key",
            name="uq_events_scope_key",
        ),
        Index("ix_events_start_ts", "event_time"),
        Index("ix_events_chart", "chart_id"),
        Index("ix_events_module_channel", "module", "channel"),
        Index(
            "ix_events_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_events_event_time_scope", "event_time", "module", "channel"),
        Index("ix_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="RESTRICT"), nullable=True

    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"), nullable=True
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default=text("'pending'")
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)


    key = synonym("event_key")
    type = synonym("event_type")
    start_ts = synonym("event_time")


    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RulesetVersion | None] = relationship(
        back_populates="events"
    )
    severity_profile: Mapped[SeverityProfile | None] = relationship(
        back_populates="events"
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")

    def __init__(self, **kwargs: Any) -> None:
        event_key = kwargs.pop("event_key", None)
        start_ts = kwargs.pop("start_ts", None)
        event_time = kwargs.pop("event_time", None)
        event_type = kwargs.pop("event_type", None)
        objects = kwargs.pop("objects", None)
        payload = kwargs.pop("payload", None)

        resolved_time = _ensure_utc(event_time or start_ts or datetime.now(timezone.utc))
        kwargs.setdefault("event_time", resolved_time)

        if event_type is not None:
            if isinstance(event_type, EventType):
                kwargs.setdefault("event_type", event_type.value)
            else:
                try:
                    kwargs.setdefault("event_type", EventType(str(event_type)).value)
                except ValueError:
                    kwargs.setdefault("event_type", str(event_type))
        else:
            kwargs.setdefault("event_type", EventType.custom.value)

        data = payload or {}
        if objects is not None:
            data = dict(data)
            data.setdefault("objects", objects)
        kwargs.setdefault("payload", data)

        kwargs.setdefault("event_key", str(event_key or uuid4().hex))


        super().__init__(**kwargs)

    @property
    def objects(self) -> dict[str, Any] | None:
        return (self.payload or {}).get("objects") if self.payload is not None else None


class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Auxiliary metadata for asteroid lookups."""

    __tablename__ = "asteroid_meta"
    __table_args__ = _table_args(
        UniqueConstraint("designation", name="uq_asteroid_designation"),
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "designation",
            name="uq_asteroid_meta_scope_designation",
        ),
        Index(
            "ix_asteroid_meta_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_asteroid_meta_created_at", "created_at"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asteroid_id: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: f"asteroid-{uuid4().hex}"
    )
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    common_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    name = synonym("common_name")

    def __init__(self, **kwargs: Any) -> None:
        designation = kwargs.pop("designation", None)
        common_name = kwargs.pop("common_name", None)
        name = kwargs.pop("name", None)
        attributes = kwargs.pop("attributes", None)

        if designation is not None:
            kwargs.setdefault("designation", str(designation))

        if common_name is None and name is not None:
            common_name = name

        if common_name is not None:
            kwargs.setdefault("common_name", str(common_name))

        kwargs.setdefault("attributes", attributes or {})

        super().__init__(**kwargs)


    @property
    def display_name(self) -> str | None:
        return self.common_name or self.designation


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued exports for downstream delivery."""

    __tablename__ = "export_jobs"
    __table_args__ = _table_args(
        UniqueConstraint(
            "module",
            "submodule",
            "channel",
            "subchannel",
            "job_key",
            name="uq_export_jobs_scope_key",
        ),
        Index(
            "ix_export_jobs_scope_full",
            "module",
            "submodule",
            "channel",
            "subchannel",
        ),
        Index("ix_export_jobs_requested_at", "requested_at"),
        Index("ix_export_jobs_completed_at", "completed_at"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )

    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    job_type: Mapped[str] = mapped_column(
        SAEnum(ExportType, name="export_job_type"), nullable=False, default=ExportType.json
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", server_default=text("'queued'")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    result_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    key = synonym("job_key")
    type = synonym("job_type")
    params = synonym("payload")

    event: Mapped[Event | None] = relationship(back_populates="export_jobs")


    def __init__(self, **kwargs: Any) -> None:
        job_key = kwargs.pop("job_key", None)
        job_type = kwargs.pop("job_type", None)

        type_alias = kwargs.pop("type", None)
        payload = kwargs.pop("payload", None)
        params = kwargs.pop("params", None)

        kwargs.setdefault("job_key", str(job_key or uuid4().hex))

        resolved_type = job_type if job_type is not None else type_alias
        if resolved_type is not None:
            if isinstance(resolved_type, ExportType):
                kwargs.setdefault("job_type", resolved_type.value)
            else:
                try:
                    kwargs.setdefault("job_type", ExportType(str(resolved_type)).value)
                except ValueError:
                    kwargs.setdefault("job_type", str(resolved_type))
        else:
            kwargs.setdefault("job_type", ExportType.json.value)


        payload_data = params if params is not None else payload
        kwargs.setdefault("payload", payload_data or {})

        super().__init__(**kwargs)


__all__ = [
    "ChartKind",
    "EventType",
    "ExportType",
    "AsteroidMeta",
    "Chart",
    "Event",
    "ExportJob",
    "ModuleScopeMixin",
    "OrbPolicy",
    "RulesetVersion",
    "SeverityProfile",
    "TimestampMixin",
]


# Backwards compatible alias retained for legacy imports
RuleSetVersion = RulesetVersion

