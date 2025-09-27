from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, constr

NameStr = constr(strip_whitespace=True, min_length=1, max_length=80)


class OrbPolicyBase(BaseModel):
    name: NameStr
    description: Optional[str] = None
    per_object: Dict[str, float] = Field(default_factory=dict)
    per_aspect: Dict[str, float] = Field(default_factory=dict)
    adaptive_rules: Dict[str, Any] = Field(default_factory=dict)


class OrbPolicyCreate(OrbPolicyBase):
    pass


class OrbPolicyUpdate(BaseModel):
    description: Optional[str] = None
    per_object: Optional[Dict[str, float]] = None
    per_aspect: Optional[Dict[str, float]] = None
    adaptive_rules: Optional[Dict[str, Any]] = None


class OrbPolicyOut(OrbPolicyBase):
    id: int


class Paging(BaseModel):
    limit: int
    offset: int
    total: int


class OrbPolicyListOut(BaseModel):
    items: list[OrbPolicyOut]
    paging: Paging
