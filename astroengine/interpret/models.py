

"""Pydantic models and runtime dataclasses for interpretation rulepacks."""


from __future__ import annotations

from dataclasses import dataclass


from datetime import UTC, datetime
from typing import Any, Iterable, Literal, Mapping, Sequence


from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS


from dataclasses import dataclass
from typing import Any, Iterable, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator



Body = Literal[
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Node",
]


Aspect = Literal[0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180]
Scope = Literal["synastry", "composite", "davison"]


@dataclass(frozen=True)
class RuleWhen:
    bodiesA: tuple[str, ...] | str
    bodiesB: tuple[str, ...] | str
    aspects: tuple[int, ...] | str
    min_severity: float


@dataclass(frozen=True)
class RuleThen:
    title: str
    tags: tuple[str, ...]
    base_score: float
    score_fn: str
    markdown_template: str | None = None


@dataclass(frozen=True)
class Rule:
    id: str
    scope: str
    when: RuleWhen
    then: RuleThen


@dataclass(frozen=True)
class Rulepack:
    rulepack: str
    profiles: dict[str, dict[str, Any]]
    rules: tuple[Rule, ...]
    source: str | None = None

    def profile_weights(self, profile: str) -> dict[str, float]:
        data = self.profiles.get(profile)
        if data is None:
            data = self.profiles.get("balanced")
        if data is None:
            if self.profiles:
                _, data = next(iter(self.profiles.items()))
            else:
                return {}
        tags = data.get("tags") or data.get("tag_weights") or {}
        return {str(k): float(v) for k, v in tags.items()}


class RulepackMeta(BaseModel):
    """Metadata describing a stored rulepack version."""

    id: str
    name: str
    version: int
    title: str
    description: str | None = None
    created_at: AwareDatetime
    mutable: bool = False
    available_versions: list[int] = Field(default_factory=list)


class FindingsFilters(BaseModel):
    """Filtering controls for interpretation results."""

    profile: str = "balanced"
    top_k: int | None = Field(default=50, ge=1)
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    include_tags: list[str] | None = None
    exclude_tags: list[str] | None = None


class SynastryHitsInput(BaseModel):
    """Direct synastry hits payload."""

    hits: list[dict[str, Any]]


class SynastryPositionsInput(BaseModel):
    """Synastry positions payload used to compute hits in-process."""

    positionsA: dict[str, float]
    positionsB: dict[str, float]
    aspects: tuple[Aspect, ...] | None = None
    policy: dict[str, Any] | None = None

    @field_validator("positionsA", "positionsB", mode="before")
    @classmethod
    def _normalize_positions(cls, value: Any) -> dict[str, float]:
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
        raise TypeError("positions must be mappings")


class CompositePositionsInput(BaseModel):
    positions: dict[str, float]

    @field_validator("positions", mode="before")
    @classmethod
    def _normalize_positions(cls, value: Any) -> dict[str, float]:
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
        raise TypeError("positions must be mappings")


class DavisonPositionsInput(BaseModel):
    positions: dict[str, float]

    @field_validator("positions", mode="before")
    @classmethod
    def _normalize_positions(cls, value: Any) -> dict[str, float]:
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
        raise TypeError("positions must be mappings")


class InterpretRequest(BaseModel):
    """Request payload for `/relationship` evaluations."""

    rulepack_id: str
    scope: Scope = "synastry"
    filters: FindingsFilters = Field(default_factory=FindingsFilters)
    synastry: SynastryHitsInput | SynastryPositionsInput | None = None
    composite: CompositePositionsInput | None = None
    davison: DavisonPositionsInput | None = None

    model_config = ConfigDict(extra="ignore")


class Finding(BaseModel):
    """Single interpretation finding returned to clients."""

    id: str
    title: str
    tags: list[str]
    score: float
    context: dict[str, Any] = Field(default_factory=dict)


class InterpretResponse(BaseModel):
    """Response payload describing evaluated findings."""

    findings: list[Finding]
    totals: dict[str, Any]
    rulepack: RulepackMeta


class ProfileDefinition(BaseModel):
    """Profile weighting configuration for a rulepack."""

    base_multiplier: float = 1.0
    tag_weights: dict[str, float] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("tags", "tag_weights"),
    )
    rule_weights: dict[str, float] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("rule_weights", "rules"),
    )

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy(cls, value: Any) -> Mapping[str, Any] | Any:
        if isinstance(value, Mapping):
            data = dict(value)
            if "tags" in data and "tag_weights" not in data:
                data["tag_weights"] = data.pop("tags")
            return data
        return value

    @field_validator("tag_weights", "rule_weights", mode="before")
    @classmethod
    def _coerce_mapping(cls, value: Any) -> dict[str, float]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
        raise TypeError("weights must be mappings")


class RuleCondition(BaseModel):
    """Condition block inside a rule definition with legacy compatibility."""

    bodies: tuple[str, ...] | None = None
    bodiesA: tuple[str, ...] | str | None = None
    bodiesB: tuple[str, ...] | str | None = None
    aspects: tuple[int, ...] | str | None = None
    aspect_in: tuple[str, ...] | None = None
    min_severity: float | None = Field(default=None, ge=0.0)
    longitude_ranges: tuple[tuple[float, float], ...] | None = None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _coerce_payload(cls, value: Any) -> Mapping[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("when must be a mapping")
        data = dict(value)

        # Legacy `bodies` field → directional bodiesA/bodiesB
        if "bodiesA" not in data and "bodies" in data:
            bodies = data.get("bodies")
            if isinstance(bodies, Sequence) and not isinstance(bodies, (str, bytes)):
                bodies = [str(item) for item in bodies]
            elif bodies is None:
                bodies = []
            else:
                bodies = [str(bodies)]
            data["bodiesA"] = tuple(bodies[:1]) or "*"
            data["bodiesB"] = tuple(bodies[1:2]) or "*"
        if "bodiesB" not in data and "bodiesA" in data:
            data.setdefault("bodiesB", "*")
        if "bodiesA" not in data and "bodiesB" in data:
            data.setdefault("bodiesA", "*")

        # Legacy aspect names → numeric degrees
        if "aspects" not in data and "aspect_in" in data:
            names = data.get("aspect_in")
            if isinstance(names, Sequence) and not isinstance(names, (str, bytes)):
                converted: list[int] = []
                for name in names:
                    angle = BASE_ASPECTS.get(str(name).lower())
                    if angle is not None:
                        converted.append(int(round(float(angle))))
                data["aspects"] = tuple(converted) if converted else "*"
        if "aspect_in" not in data and "aspects" in data:
            aspects = data.get("aspects")
            if aspects == "*":
                data["aspect_in"] = None
            else:
                aspect_values = (
                    aspects
                    if isinstance(aspects, Sequence) and not isinstance(aspects, (str, bytes))
                    else [aspects]
                )
                names: list[str] = []
                for value in aspect_values:
                    try:
                        degree = int(round(float(value)))
                    except (TypeError, ValueError):
                        continue
                    name = _ASPECT_NAMES_BY_DEGREE.get(degree)
                    if name:
                        names.append(name)
                data["aspect_in"] = tuple(names) if names else None
        return data

    @field_validator("bodies", "aspect_in", mode="before")

    @classmethod
    def _normalize_bodies(cls, value: Any) -> tuple[str, ...] | None:
        if value is None:
            return None
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @field_validator("bodiesA", "bodiesB", mode="before")
    @classmethod

    def _normalize_directional(cls, value: Any) -> tuple[str, ...] | str | None:
        if value in (None, "*"):

            return "*"
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @field_validator("aspects", mode="before")
    @classmethod
    def _normalize_aspects(cls, value: Any) -> tuple[int, ...] | str | None:
        if value in (None, "*"):
            return "*"
        result: list[int] = []
        source = value
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            source = value
        else:
            source = [value]
        for entry in source:
            try:
                degree = int(round(float(entry)))
            except (TypeError, ValueError):
                continue
            result.append(degree)
        return tuple(result) if result else "*"


    @field_validator("longitude_ranges", mode="before")
    @classmethod
    def _normalize_ranges(cls, value: Any) -> tuple[tuple[float, float], ...] | None:
        if value is None:
            return None
        ranges: list[tuple[float, float]] = []
        for entry in value:
            lo, hi = entry
            ranges.append((float(lo), float(hi)))
        return tuple(ranges)


class RuleThen(BaseModel):
    """Consequences block for a rule."""

    title: str
    tags: tuple[str, ...] = Field(default_factory=tuple)
    base_score: float = Field(default=1.0, ge=0.0)
    score_fn: str = "linear"
    markdown_template: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)


class RuleDefinition(BaseModel):
    """Single interpretation rule supporting legacy and modern payloads."""

    id: str
    scope: Scope
    title: str | None = None
    text: str | None = None
    score: float = 1.0
    description: str | None = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    when: RuleCondition = Field(default_factory=RuleCondition)

    then: RuleThen

    @model_validator(mode="before")
    @classmethod
    def _coerce_payload(cls, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("rule definition must be a mapping")
        data = dict(value)
        then = data.get("then")
        if not isinstance(then, Mapping):
            then = {}
        title = then.get("title") or data.get("title") or str(data.get("id"))
        tags = then.get("tags") or data.get("tags") or []
        base_score = then.get("base_score", data.get("score", 1.0))
        markdown = then.get("markdown_template") or data.get("text")
        score_fn = then.get("score_fn", data.get("score_fn", "linear"))
        data.setdefault("title", title)
        data.setdefault("tags", tags)
        data.setdefault("score", base_score)
        data.setdefault("text", markdown or title)
        data["then"] = {
            "title": title,
            "tags": tags,
            "base_score": base_score,
            "score_fn": score_fn,
            "markdown_template": markdown,
        }
        return data


    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @model_validator(mode="after")

    def _sync_then(self) -> "RuleDefinition":
        object.__setattr__(self, "tags", tuple(self.then.tags))
        object.__setattr__(self, "score", float(self.then.base_score))
        if not self.text:
            object.__setattr__(self, "text", self.then.title)

        return self


class RulepackHeader(BaseModel):
    """Metadata embedded within a rulepack document."""

    id: str | None = None
    name: str | None = None
    title: str | None = None
    description: str | None = None
    version: int | None = None
    mutable: bool = False


    @model_validator(mode="before")
    @classmethod
    def _fill_defaults(cls, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("meta must be a mapping")
        data = dict(value)
        title = data.get("title")
        identifier = data.get("id")
        name = data.get("name")
        if not identifier:
            identifier = data.get("rulepack") or (title.replace(" ", "_") if title else None)
        if not identifier:
            raise ValueError("meta.id is required")
        if not name:
            name = title or identifier
        data["id"] = str(identifier)
        data["name"] = str(name)
        return data



class RulepackDocument(BaseModel):
    """Fully parsed rulepack document supporting modern payloads."""


    rulepack: str
    version: int = 1
    meta: RulepackHeader
    profiles: dict[str, ProfileDefinition] = Field(default_factory=dict)
    rules: list[RuleDefinition]
    archetypes: dict[str, list[str]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("rulepack payload must be a mapping")
        data = dict(value)
        meta = dict(data.get("meta") or {})
        rulepack_id = data.get("rulepack") or meta.get("id")
        if not rulepack_id:
            raise ValueError("rulepack identifier missing")
        meta.setdefault("id", rulepack_id)
        meta.setdefault("name", meta.get("title") or rulepack_id)
        meta.setdefault("version", data.get("version"))
        data["rulepack"] = str(rulepack_id)
        data.setdefault("version", int(meta.get("version") or data.get("version") or 1))
        data["meta"] = meta
        return data


    @field_validator("profiles", mode="before")
    @classmethod
    def _normalize_profiles(cls, value: Any) -> dict[str, dict[str, Any]]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
        raise TypeError("profiles must be mappings")

    @field_validator("rules", mode="before")
    @classmethod
    def _normalize_rules(cls, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise TypeError("rules must be an array")
        return value

    @field_validator("archetypes", mode="before")
    @classmethod
    def _normalize_archetypes(cls, value: Any) -> dict[str, tuple[str, ...]]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): tuple(str(item) for item in v) for k, v in value.items()}
        raise TypeError("archetypes must be mappings")


class RulepackVersionPayload(BaseModel):
    """Envelope returned when fetching a rulepack."""

    meta: RulepackMeta
    profiles: dict[str, ProfileDefinition]
    rules: list[RuleDefinition]
    version: int
    etag: str
    content: dict[str, Any]
    mutable: bool

    model_config = ConfigDict(extra="ignore")


class RulepackLintResult(BaseModel):
    """Lint outcome for a rulepack upload attempt."""

    ok: bool
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


def now_utc() -> datetime:
    """Utility returning timezone-aware UTC now for metadata stamping."""

    return datetime.now(tz=UTC)


@dataclass(slots=True)
class RuleWhen:
    """Runtime representation of a rule's condition."""


    bodiesA: tuple[str, ...] | str
    bodiesB: tuple[str, ...] | str
    aspects: tuple[int, ...] | str
    min_severity: float



@dataclass(slots=True)
class RuleThenRuntime:
    """Runtime representation of a rule's consequence block."""


    title: str
    tags: tuple[str, ...]
    base_score: float
    score_fn: str
    markdown_template: str | None = None



@dataclass(slots=True)
class Rule:
    """Runtime rule combining condition and consequences."""

    id: str
    scope: Scope
    when: RuleWhen
    then: RuleThenRuntime



@dataclass(slots=True)
class Rulepack:

    """Runtime rulepack used by the interpretation engine."""

    id: str
    version: int
    profiles: dict[str, ProfileDefinition]
    archetypes: dict[str, list[str]]
    rules: list[Rule]

    def profile_weights(self, profile_name: str) -> dict[str, float]:
        profile = self.profiles.get(profile_name) or self.profiles.get("balanced")
        if profile is None:
            return {}
        base = float(profile.base_multiplier)
        if not profile.tag_weights:
            return {}
        return {tag: float(weight) * base for tag, weight in profile.tag_weights.items()}


_ASPECT_NAMES_BY_DEGREE = {int(round(angle)): name for name, angle in BASE_ASPECTS.items()}


__all__ = [
    "Body",
    "Aspect",
    "Scope",
    "RulepackMeta",
    "FindingsFilters",
    "InterpretRequest",
    "InterpretResponse",
    "Finding",
    "ProfileDefinition",
    "RuleCondition",
    "RuleThen",
    "RuleDefinition",
    "RulepackHeader",
    "RulepackDocument",
    "RulepackVersionPayload",
    "RulepackLintResult",
    "RuleWhen",
    "RuleThenRuntime",
    "Rule",
    "Rulepack",
    "now_utc",
]


