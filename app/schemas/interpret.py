from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Scope = Literal["synastry", "composite", "davison"]


class RulepackInfo(BaseModel):
    id: str
    path: str
    description: str | None = None


class FindingsRequest(BaseModel):
    scope: Scope
    # One of these, depending on scope
    hits: list[dict[str, Any]] | None = None
    positions: dict[str, float] | None = None
    houses: dict[str, Any] | None = None
    angles: dict[str, float] | None = None

    # Rules source
    rulepack_id: str | None = None
    rules_inline: Any | None = None

    # Filters
    top_k: int | None = Field(default=None, ge=1)
    min_score: float | None = Field(default=None, ge=0.0)
    profile: str | None = None


class FindingOut(BaseModel):
    id: str
    scope: Scope
    title: str
    text: str
    score: float
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class FindingsResponse(BaseModel):
    findings: list[FindingOut]
    meta: dict[str, Any] = Field(default_factory=dict)


class RulepacksResponse(BaseModel):
    items: list[RulepackInfo]
    meta: dict[str, Any] = Field(default_factory=dict)
