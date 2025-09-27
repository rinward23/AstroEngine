"""SQLAlchemy models backing the AstroEngine Plus API test harness."""

from __future__ import annotations


import uuid
from datetime import datetime

from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy.sql import func

from .base import Base



def _uuid_hex() -> str:
    """Generate random hexadecimal identifiers for primary keys."""

    return uuid.uuid4().hex



class TimestampMixin:
    """Adds creation and update timestamps to persisted records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
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
        String(64),
        nullable=False,
        default="plus",
        server_default=text("'plus'"),
    )
    submodule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="transits",
        server_default=text("'transits'"),
    )
    subchannel: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Orb widths for aspects; supports both legacy and modern schemas."""

    __tablename__ = "orb_policies"

    __table_args__ = (
        UniqueConstraint(
            "profile_key", "body", "aspect", name="uq_orb_policy_legacy"
        ),

    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Legacy columns exercised directly in tests
    profile_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default"
    )
    body: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aspect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    orb_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Rich policy definition used by the Plus API
    name: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_object: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    per_aspect: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    adaptive_rules: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        body = kwargs.pop("body", None)
        aspect = kwargs.pop("aspect", None)
        orb_degrees = kwargs.pop("orb_degrees", None)

        if profile_key is not None:
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

        kwargs.setdefault("adaptive_rules", {})
        kwargs["per_object"] = per_object
        kwargs["per_aspect"] = per_aspect

        if "name" not in kwargs:
            tokens = [profile_key or "policy", body or "object", aspect or "aspect"]
            kwargs["name"] = ":".join(str(token) for token in tokens)

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = profile_key
        if body is not None:
            self.body = body
        if aspect is not None:
            self.aspect = aspect
        if orb_degrees is not None:
            self.orb_degrees = float(orb_degrees)


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Store severity weights used during scoring routines."""

    __tablename__ = "severity_profiles"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weights: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    name = synonym("profile_key")

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Support legacy ``name`` keyword aliasing ``profile_key``."""

        name = kwargs.pop("name", None)
        super().__init__(*args, **kwargs)
        if name is not None:
            self.profile_key = str(name)

    @property
    def name(self) -> str:
        return self.profile_key

    @name.setter
    def name(self, value: str) -> None:
        self.profile_key = value


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        weights = kwargs.pop("weights", None)
        modifiers = kwargs.pop("modifiers", None)

        if profile_key is not None:
            kwargs.setdefault("name", str(profile_key))

        if weights is not None:
            kwargs["weights"] = weights
        else:
            kwargs.setdefault("weights", {})

        if modifiers is not None:
            kwargs["modifiers"] = modifiers

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = profile_key



class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Persisted chart metadata plus arbitrary serialized payloads."""

    __tablename__ = "charts"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dt_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used throughout tests."""

        dt_utc = kwargs.pop("dt_utc", None)
        kind = kwargs.pop("kind", None)
        chart_key = kwargs.pop("chart_key", None)
        profile_key = kwargs.pop("profile_key", None)
        super().__init__(*args, **kwargs)
        if dt_utc is not None:
            self.reference_time = dt_utc
        if kind is not None:
            self.kind = kind.value if isinstance(kind, ChartKind) else str(kind)
        self.chart_key = str(chart_key) if chart_key is not None else uuid4().hex
        if profile_key is not None:
            self.profile_key = str(profile_key)
        elif not getattr(self, "profile_key", None):
            self.profile_key = "default"

    @property
    def dt_utc(self) -> datetime | None:
        return self.reference_time

    @dt_utc.setter
    def dt_utc(self, value: datetime | None) -> None:
        self.reference_time = value



class RulesetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rule bundles consumed by scans and exports."""

    __tablename__ = "ruleset_versions"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ruleset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    definition: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )


    def __init__(self, **kwargs: Any) -> None:
        ruleset_key = kwargs.pop("ruleset_key", None)
        if ruleset_key is not None:
            kwargs.setdefault("key", str(ruleset_key))

        version_value = kwargs.pop("version", None)
        if version_value is not None:
            kwargs["version"] = _coerce_version_value(version_value)
        else:
            kwargs.setdefault("version", 1)

        definition = kwargs.pop("definition", None)
        if definition is not None:
            kwargs.setdefault("definition_json", definition)

        super().__init__(**kwargs)

        if ruleset_key is not None:
            self.ruleset_key = str(ruleset_key)


    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")


    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Allow ``key`` to alias ``ruleset_key`` for backwards compatibility."""

        key = kwargs.pop("key", None)
        definition_json = kwargs.pop("definition_json", None)
        checksum = kwargs.pop("checksum", None)
        super().__init__(*args, **kwargs)
        if key is not None:
            self.ruleset_key = str(key)
        if definition_json is not None:
            self.definition = definition_json
        if checksum is not None:
            self.checksum = str(checksum)
        elif not getattr(self, "checksum", None):
            self.checksum = uuid4().hex

    @property
    def key(self) -> str:
        return self.ruleset_key

    @key.setter
    def key(self, value: str) -> None:
        self.ruleset_key = value



class Event(ModuleScopeMixin, TimestampMixin, Base):
    """Detected events referencing source charts and rulesets."""

    __tablename__ = "events"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("charts.id", ondelete="CASCADE"), nullable=False
    )
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="SET NULL"), nullable=True

    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"), nullable=True
    )

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default=text("'pending'")
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RulesetVersion | None] = relationship(
        back_populates="events"
    )
    severity_profile: Mapped[SeverityProfile | None] = relationship(
        back_populates="events"
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used in fixtures and tests."""

        event_key = kwargs.pop("event_key", None)
        event_type = kwargs.pop("type", None)
        start_ts = kwargs.pop("start_ts", None)
        objects = kwargs.pop("objects", None)
        super().__init__(*args, **kwargs)
        self.event_key = str(event_key or uuid4().hex)
        if event_type is not None:
            self.event_type = (
                event_type.value if isinstance(event_type, EventType) else str(event_type)
            )
        if start_ts is not None:
            self.event_time = start_ts
        if objects is not None:
            payload = dict(self.payload or {})
            payload.setdefault("objects", objects)
            self.payload = payload

    @property
    def type(self) -> EventType | str:
        try:
            return EventType(self.event_type)
        except ValueError:
            return self.event_type

    @type.setter
    def type(self, value: EventType | str) -> None:
        self.event_type = value.value if isinstance(value, EventType) else str(value)

    @property
    def start_ts(self) -> datetime:
        return self.event_time

    @start_ts.setter
    def start_ts(self, value: datetime) -> None:
        self.event_time = value


    def __init__(self, **kwargs: Any) -> None:
        event_time = kwargs.pop("event_time", None)
        if event_time is None:
            event_time = kwargs.pop("start_ts", None)
        if event_time is None:
            event_time = datetime.now(timezone.utc)
        elif isinstance(event_time, datetime) and event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        kwargs.setdefault("start_ts", event_time)

        event_type = kwargs.pop("event_type", None)
        if event_type is not None:
            if isinstance(event_type, EventType):
                kwargs.setdefault("type", event_type)
            else:
                try:
                    kwargs.setdefault("type", EventType(str(event_type)))
                except Exception:
                    kwargs.setdefault("type", EventType.custom)
        elif "type" not in kwargs:
            kwargs["type"] = EventType.custom

        payload = kwargs.pop("payload", None)
        if payload is not None:
            kwargs.setdefault("payload", payload)

        objects = kwargs.pop("objects", None)
        if objects is not None:
            kwargs.setdefault("objects", objects)

        super().__init__(**kwargs)



class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Auxiliary metadata for asteroid lookups."""

    __tablename__ = "asteroid_meta"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asteroid_id: Mapped[str] = mapped_column(String(64), nullable=False)
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    common_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Allow legacy keyword aliases and sensible defaults."""

        name = kwargs.pop("name", None)
        designation = kwargs.get("designation")
        asteroid_id = kwargs.pop("asteroid_id", None)
        attributes = kwargs.pop("attributes", None)
        super().__init__(*args, **kwargs)
        if asteroid_id is None and designation is not None:
            self.asteroid_id = str(designation)
        elif asteroid_id is not None:
            self.asteroid_id = str(asteroid_id)
        if name is not None:
            self.common_name = str(name)
        elif not getattr(self, "common_name", None):
            self.common_name = str(designation) if designation is not None else ""
        if attributes is None and not getattr(self, "attributes", None):
            self.attributes = {}
        elif attributes is not None:
            self.attributes = dict(attributes)


    def __init__(self, **kwargs: Any) -> None:
        asteroid_id = kwargs.pop("asteroid_id", None)
        if "designation" not in kwargs and asteroid_id is not None:
            kwargs["designation"] = str(asteroid_id)
        common_name = kwargs.pop("common_name", None)
        if "name" not in kwargs and common_name is not None:
            kwargs["name"] = common_name
        attributes = kwargs.pop("attributes", None)
        if attributes is not None:
            kwargs.setdefault("attributes", attributes)
        else:
            kwargs.setdefault("attributes", {})
        super().__init__(**kwargs)

        if common_name is not None:
            self.common_name = common_name



class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued exports for downstream delivery."""

    __tablename__ = "export_jobs"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True

    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", server_default=text("'queued'")
    )

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

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used in repositories."""

        job_type = kwargs.pop("type", None)
        params = kwargs.pop("params", None)
        job_key = kwargs.pop("job_key", None)
        super().__init__(*args, **kwargs)
        if job_type is not None:
            self.job_type = job_type.value if isinstance(job_type, ExportType) else str(job_type)
        if params is not None:
            self.payload = params
        self.job_key = str(job_key) if job_key is not None else uuid4().hex


    def __init__(self, **kwargs: Any) -> None:
        job_type = kwargs.pop("job_type", None)
        if job_type is not None:
            if isinstance(job_type, ExportType):
                kwargs.setdefault("type", job_type)
            else:
                try:
                    kwargs.setdefault("type", ExportType(str(job_type)))
                except Exception:
                    kwargs.setdefault("type", ExportType.json)

        payload = kwargs.pop("payload", None)
        params = kwargs.pop("params", None)
        if payload is not None and params is None:
            params = payload
        if params is not None:
            kwargs.setdefault("params", params)
        else:
            kwargs.setdefault("params", {})

        resolved_type = kwargs.get("type")

        super().__init__(**kwargs)

        if resolved_type is not None:
            if isinstance(resolved_type, ExportType):
                self.job_type = resolved_type.value
            else:
                self.job_type = str(resolved_type)



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


# Backwards compatible alias retained for older imports
RuleSetVersion = RulesetVersion
__all__.append("RuleSetVersion")


