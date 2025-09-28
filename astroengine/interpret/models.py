"""Typed models for interpretation rulepacks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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

Aspect = Literal[0, 30, 45, 60, 72, 90, 120, 135, 150, 180]


class RuleWhen(BaseModel):
    """Conditions required for a rule to match an aspect hit."""

    model_config = ConfigDict(extra="forbid")

    bodiesA: list[Body] | Literal["*"]
    bodiesB: list[Body] | Literal["*"]
    aspects: list[int] | Literal["*"]
    min_severity: float = Field(default=0.0, ge=0.0, le=1.0)


class RuleThen(BaseModel):
    """Payload emitted when a rule matches."""

    model_config = ConfigDict(extra="forbid")

    title: str
    tags: list[str]
    base_score: float = Field(default=0.5, ge=0.0, le=1.0)
    score_fn: str = Field(default="cosine^1.0")
    markdown_template: str | None = None


class Rule(BaseModel):
    """Single interpretation rule."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scope: Literal["synastry", "composite", "davison"] = "synastry"
    when: RuleWhen
    then: RuleThen


class Profile(BaseModel):
    """Tag weight profile."""

    model_config = ConfigDict(extra="forbid")

    tags: dict[str, float]


class Rulepack(BaseModel):
    """Container for an interpretation rulepack."""

    model_config = ConfigDict(extra="forbid")

    rulepack: str
    version: int = Field(default=1, ge=1)
    meta: dict[str, Any] = Field(default_factory=dict)
    profiles: dict[str, Profile]
    archetypes: dict[str, list[str]] | None = None
    rules: list[Rule]

    def profile_weights(self, profile: str) -> dict[str, float]:
        """Return tag weights for *profile* or fall back to equal weighting."""

        if profile in self.profiles:
            return self.profiles[profile].tags
        # Fall back to average weights of the default profile when unavailable.
        default_profile = next(iter(self.profiles.values()), None)
        return default_profile.tags if default_profile else {}
