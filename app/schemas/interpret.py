from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Scope = Literal["synastry", "composite", "davison"]


class RulepackInfo(BaseModel):
    id: str
    path: str
    description: Optional[str] = None


class FindingsRequest(BaseModel):
    scope: Scope
    # One of these, depending on scope
    hits: Optional[List[Dict[str, Any]]] = None
    positions: Optional[Dict[str, float]] = None

    # Rules source
    rulepack_id: Optional[str] = None
    rules_inline: Optional[List[Dict[str, Any]]] = None

    # Filters
    top_k: Optional[int] = Field(default=None, ge=1)
    min_score: Optional[float] = Field(default=None, ge=0.0)


class FindingOut(BaseModel):
    id: str
    scope: Scope
    title: str
    text: str
    score: float
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class FindingsResponse(BaseModel):
    findings: List[FindingOut]
    meta: Dict[str, Any] = Field(default_factory=dict)


class RulepacksResponse(BaseModel):
    items: List[RulepackInfo]
    meta: Dict[str, Any] = Field(default_factory=dict)
