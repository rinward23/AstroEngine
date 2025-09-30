
"""Pydantic and dataclass models for interpretation APIs and rulepacks."""

from __future__ import annotations

from dataclasses import dataclass

from datetime import UTC, datetime
from typing import Any, Iterable, Literal

from pydantic import AliasChoices, AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


@dataclass(slots=True, frozen=True)
class RuleWhen:
    """Condition block describing when a rule activates."""

    bodiesA: tuple[str, ...] | str
    bodiesB: tuple[str, ...] | str
    aspects: tuple[int, ...] | str
    min_severity: float

    @property
    def bodies(self) -> tuple[str, ...] | None:
        """Return a normalized pair of bodies when explicitly defined."""

        if isinstance(self.bodiesA, tuple) and isinstance(self.bodiesB, tuple):
            if len(self.bodiesA) == 1 and len(self.bodiesB) == 1:
                return (self.bodiesA[0], self.bodiesB[0])
        return None

    @property
    def aspect_in(self) -> tuple[int, ...] | None:
        if isinstance(self.aspects, tuple):
            return self.aspects
        return None


@dataclass(slots=True, frozen=True)
class RuleThen:
    """Outcome block describing what happens when a rule triggers."""

    title: str
    tags: tuple[str, ...]
    base_score: float
    score_fn: str
    markdown_template: str | None = None


@dataclass(slots=True, frozen=True)
class Rule:
    """Runtime rule used by the interpretation engine."""

    id: str
    scope: str
    when: RuleWhen
    then: RuleThen


@dataclass(slots=True)
class Rulepack:
    """Loaded rulepack with helper methods for weighting profiles."""

    rulepack: str
    version: int
    profiles: dict[str, dict[str, float]]
    rules: list[Rule]
    archetypes: dict[str, tuple[str, ...]]
    meta: dict[str, Any]
    raw: dict[str, Any]

    def profile_weights(self, profile: str) -> dict[str, float]:
        """Return tag weights for *profile*, falling back gracefully."""

        if profile in self.profiles:
            return dict(self.profiles[profile])
        if "balanced" in self.profiles:
            return dict(self.profiles["balanced"])
        if self.profiles:
            first_key = sorted(self.profiles)[0]
            return dict(self.profiles[first_key])
        return {}


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

    @field_validator("tag_weights", "rule_weights", mode="before")
    @classmethod
    def _coerce_mapping(cls, value: Any) -> dict[str, float]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items()}
        raise TypeError("weights must be mappings")


class RuleCondition(BaseModel):
    """Condition block inside a rule definition."""

    bodies: tuple[str, ...] | None = Field(default=None, validation_alias=AliasChoices("bodies"))
    aspect_in: tuple[str, ...] | None = Field(default=None, validation_alias=AliasChoices("aspect_in"))
    bodiesA: tuple[str, ...] | str | None = Field(
        default=None,
        validation_alias=AliasChoices("bodiesA", "bodies_a"),
    )
    bodiesB: tuple[str, ...] | str | None = Field(
        default=None,
        validation_alias=AliasChoices("bodiesB", "bodies_b"),
    )
    aspects: tuple[Any, ...] | str | None = Field(
        default=None,
        validation_alias=AliasChoices("aspects"),
    )
    min_severity: float | None = Field(default=None, ge=0.0)
    longitude_ranges: tuple[tuple[float, float], ...] | None = None

    @field_validator("bodies", mode="before")
    @classmethod
    def _normalize_bodies(cls, value: Any) -> tuple[str, ...] | None:
        if value is None:
            return None
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @field_validator("bodiesA", "bodiesB", mode="before")
    @classmethod
    def _normalize_body_side(cls, value: Any) -> tuple[str, ...] | str | None:
        if value is None:
            return None
        if value == "*":
            return "*"
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @field_validator("aspect_in", mode="before")
    @classmethod
    def _normalize_aspect_names(cls, value: Any) -> tuple[str, ...] | None:
        if value is None:
            return None
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @field_validator("aspects", mode="before")
    @classmethod
    def _normalize_aspects(cls, value: Any) -> tuple[Any, ...] | str | None:
        if value is None:
            return None
        if value == "*":
            return "*"
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(value)
        return (value,)

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


class RuleDefinition(BaseModel):
    """Single interpretation rule."""

    id: str
    scope: Scope
    title: str | None = None
    text: str | None = None
    score: float = 1.0
    description: str | None = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    when: RuleCondition = Field(default_factory=RuleCondition)
    markdown_template: str | None = None
    then: RuleOutcome | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(str(item) for item in value)
        return (str(value),)

    @model_validator(mode="after")
    def _populate_then(self) -> "RuleDefinition":
        if self.then is None:
            self.then = RuleOutcome(
                title=self.title or self.id,
                tags=self.tags,
                base_score=float(self.score),
                score_fn="linear",
                markdown_template=self.markdown_template or self.text,
            )
        elif self.title is None:
            self.title = self.then.title
        if self.markdown_template is None and self.then.markdown_template is not None:
            self.markdown_template = self.then.markdown_template
        return self


class RulepackHeader(BaseModel):
    """Metadata embedded within a rulepack document."""

    id: str | None = None
    name: str | None = None
    title: str | None = None
    description: str | None = None
    version: int | None = None
    mutable: bool = False

    model_config = ConfigDict(extra="allow")


class RulepackDocument(BaseModel):
    """Fully parsed rulepack document."""

    rulepack: str | None = None
    version: int | None = None
    meta: RulepackHeader | None = None
    profiles: dict[str, ProfileDefinition] = Field(default_factory=dict)
    rules: list[RuleDefinition]
    archetypes: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

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


class RuleOutcome(BaseModel):
    """Result block describing effects of a matched rule."""

    title: str
    tags: tuple[str, ...] = Field(default_factory=tuple)
    base_score: float = Field(default=0.5, ge=0.0)
    score_fn: str = "linear"
    markdown_template: str | None = None

    model_config = ConfigDict(extra="allow")


@dataclass(frozen=True, slots=True)
class RuleWhen:
    """Runtime representation of the `when` predicate."""

    bodiesA: tuple[str, ...] | str
    bodiesB: tuple[str, ...] | str
    aspects: tuple[int, ...] | str
    min_severity: float


@dataclass(frozen=True, slots=True)
class RuleThen:
    """Runtime representation of the `then` payload."""

    title: str
    tags: tuple[str, ...]
    base_score: float
    score_fn: str
    markdown_template: str | None = None


@dataclass(frozen=True, slots=True)
class Rule:
    """Evaluation-ready interpretation rule."""

    id: str
    scope: str
    when: RuleWhen
    then: RuleThen


@dataclass(slots=True)
class Rulepack:
    """Evaluation-ready rulepack with helper utilities."""

    id: str
    version: int
    profiles: dict[str, ProfileDefinition] = field(default_factory=dict)
    rules: tuple[Rule, ...] = field(default_factory=tuple)
    archetypes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def profile_weights(self, profile: str) -> dict[str, float]:
        if not self.profiles:
            return {}
        if profile in self.profiles:
            definition = self.profiles[profile]
        elif "balanced" in self.profiles:
            definition = self.profiles["balanced"]
        else:
            key = sorted(self.profiles)[0]
            definition = self.profiles[key]
        weights = {tag: float(weight) for tag, weight in definition.tag_weights.items()}
        base = float(definition.base_multiplier)
        if base != 1.0:
            weights = {tag: weight * base for tag, weight in weights.items()}
        return weights


@dataclass(slots=True)
class LoadedRulepack(Rulepack):
    """Rulepack along with its validated document and raw payload."""

    document: RulepackDocument | None = None
    content: dict[str, Any] = field(default_factory=dict)

    @property
    def rulepack(self) -> str:
        return self.id


RuleDefinition.model_rebuild()

