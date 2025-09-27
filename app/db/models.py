"""SQLAlchemy models backing the AstroEngine Plus API test harness."""

from __future__ import annotations


import uuid

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


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


def _render_orb_policy_name(profile_key: str, body: str | None, aspect: str | None) -> str:
    parts = [profile_key or "default"]
    parts.append((body or "any").lower())
    parts.append((aspect or "custom").lower())
    return ":".join(parts)


class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Aggregate orb policy definitions exposed via the Plus API."""


        kwargs.setdefault("adaptive_rules", {})
        kwargs["per_object"] = per_object
        kwargs["per_aspect"] = per_aspect

        if "name" not in kwargs:
            tokens = [profile_key or "policy", body or "object", aspect or "aspect"]
            kwargs["name"] = ":".join(str(token) for token in tokens)

        super().__init__(**kwargs)


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

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        body = kwargs.pop("body", None)
        aspect = kwargs.pop("aspect", None)
        orb_degrees = kwargs.pop("orb_degrees", None)

        per_object: Dict[str, float] = dict(kwargs.pop("per_object", {}) or {})
        per_aspect: Dict[str, float] = dict(kwargs.pop("per_aspect", {}) or {})
        adaptive_rules: Dict[str, Any] = dict(kwargs.pop("adaptive_rules", {}) or {})

        orb_value: Optional[float] = None
        if orb_degrees is not None:
            try:
                orb_value = float(orb_degrees)
            except (TypeError, ValueError):
                orb_value = None
        if orb_value is not None:
            if body:
                per_object.setdefault(str(body), orb_value)
            if aspect:
                per_aspect.setdefault(str(aspect).lower(), orb_value)

        kwargs.setdefault("name", _render_orb_policy_name(profile_key or "default", body, aspect))
        kwargs["per_object"] = per_object
        kwargs["per_aspect"] = per_aspect
        kwargs["adaptive_rules"] = adaptive_rules
        kwargs["profile_key"] = profile_key or "default"
        kwargs["body"] = body
        kwargs["aspect"] = aspect.lower() if isinstance(aspect, str) else aspect
        kwargs["orb_degrees"] = orb_value

        super().__init__(**kwargs)



class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Store severity weights used during scoring routines."""

    __tablename__ = "severity_profiles"


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    name = synonym("profile_key")

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        weights = kwargs.pop("weights", None)
        if profile_key is not None:
            kwargs["profile_key"] = profile_key
        if weights is not None:
            kwargs["weights"] = weights
        kwargs.setdefault("name", f"{kwargs.get('profile_key', 'default')}_severity")
        super().__init__(**kwargs)



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


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        if profile_key is not None:
            kwargs["profile_key"] = profile_key
        data = kwargs.pop("data", None)
        if data is not None:
            kwargs["data"] = data
            if "kind" not in kwargs and isinstance(data, dict):
                kind_value = data.get("kind")
                if isinstance(kind_value, str):
                    try:
                        kwargs["kind"] = ChartKind(kind_value)
                    except ValueError:
                        try:
                            kwargs["kind"] = ChartKind[kind_value]
                        except Exception:
                            kwargs["kind"] = ChartKind.custom
        if "kind" not in kwargs:
            kwargs["kind"] = ChartKind.custom
        if "dt_utc" not in kwargs or kwargs["dt_utc"] is None:
            kwargs["dt_utc"] = datetime.now(timezone.utc)
        kwargs.setdefault("lat", 0.0)
        kwargs.setdefault("lon", 0.0)
        super().__init__(**kwargs)



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

    def __init__(self, **kwargs: Any) -> None:
        ruleset_key = kwargs.pop("ruleset_key", None)
        definition = kwargs.pop("definition", None)
        if ruleset_key is not None and "key" not in kwargs:
            kwargs["key"] = str(ruleset_key)
        if definition is not None and "definition_json" not in kwargs:
            kwargs["definition_json"] = definition
        version_value = kwargs.get("version")
        if isinstance(version_value, str):
            try:
                kwargs["version"] = int(float(version_value))
            except ValueError:
                pass
        super().__init__(**kwargs)


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


    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

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


    def __init__(self, **kwargs: Any) -> None:
        event_time = kwargs.pop("event_time", None)
        if event_time is not None and "start_ts" not in kwargs:
            kwargs["start_ts"] = event_time
        event_type = kwargs.pop("event_type", None)
        if event_type is not None and "type" not in kwargs:
            if isinstance(event_type, EventType):
                kwargs["type"] = event_type
            else:
                try:
                    kwargs["type"] = EventType(event_type)
                except ValueError:
                    try:
                        kwargs["type"] = EventType[event_type]
                    except Exception:
                        kwargs["type"] = EventType.custom
        if "objects" not in kwargs:
            payload = kwargs.get("payload")
            if isinstance(payload, dict) and "objects" in payload:
                kwargs["objects"] = payload["objects"]
        kwargs.setdefault("objects", {})
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


    def __init__(self, **kwargs: Any) -> None:
        asteroid_id = kwargs.pop("asteroid_id", None)
        common_name = kwargs.pop("common_name", None)
        if asteroid_id is not None and "designation" not in kwargs:
            kwargs["designation"] = str(asteroid_id)
        if common_name is not None and "name" not in kwargs:
            kwargs["name"] = str(common_name)
        super().__init__(**kwargs)

    @property
    def common_name(self) -> str | None:
        return self.name

    @common_name.setter
    def common_name(self, value: str | None) -> None:
        self.name = value if value is not None else self.name



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


    def __init__(self, **kwargs: Any) -> None:
        job_type = kwargs.pop("job_type", None)
        if job_type is not None and "type" not in kwargs:
            if isinstance(job_type, ExportType):
                kwargs["type"] = job_type
            else:
                try:
                    kwargs["type"] = ExportType(job_type)
                except ValueError:
                    try:
                        kwargs["type"] = ExportType[job_type]
                    except Exception:
                        kwargs["type"] = ExportType.json
        payload = kwargs.pop("payload", None)
        if payload is not None and "params" not in kwargs:
            kwargs["params"] = payload
        super().__init__(**kwargs)

    @property
    def job_type(self) -> str:
        return self.type.value

    @job_type.setter
    def job_type(self, value: str) -> None:
        self.type = ExportType(value)

    @property
    def payload(self) -> dict[str, Any]:
        return self.params

    @payload.setter
    def payload(self, value: dict[str, Any]) -> None:
        self.params = value



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
RulesetVersion = RuleSetVersion

__all__.append("RulesetVersion")

