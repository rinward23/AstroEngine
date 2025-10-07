from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, constr

NameStr = constr(strip_whitespace=True, min_length=1, max_length=80)


class OrbPolicyBase(BaseModel):
    name: NameStr
    description: str | None = None
    per_object: dict[str, float] = Field(default_factory=dict)
    per_aspect: dict[str, float] = Field(default_factory=dict)
    adaptive_rules: dict[str, Any] = Field(default_factory=dict)


class OrbPolicyCreate(OrbPolicyBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "classic",
                "description": "Default classical orbs",
                "per_object": {"Sun": 8.0, "Moon": 6.0},
                "per_aspect": {
                    "sextile": 3.0,
                    "square": 6.0,
                    "trine": 6.0,
                    "conjunction": 8.0,
                },
                "adaptive_rules": {"luminaries_factor": 0.9, "outers_factor": 1.1},
            }
        }
    )


class OrbPolicyUpdate(BaseModel):
    description: str | None = None
    per_object: dict[str, float] | None = None
    per_aspect: dict[str, float] | None = None
    adaptive_rules: dict[str, Any] | None = None


class OrbPolicyOut(OrbPolicyBase):
    id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "classic",
                "description": "Default classical orbs",
                "per_object": {"Sun": 8.0, "Moon": 6.0},
                "per_aspect": {"sextile": 3.0, "square": 6.0},
                "adaptive_rules": {"luminaries_factor": 0.9},
            }
        }
    )


class Paging(BaseModel):
    limit: int
    offset: int
    total: int


class OrbPolicyListOut(BaseModel):
    items: list[OrbPolicyOut]
    paging: Paging

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 1,
                        "name": "classic",
                        "description": "Default classical orbs",
                        "per_object": {"Sun": 8.0, "Moon": 6.0},
                        "per_aspect": {"sextile": 3.0, "square": 6.0},
                        "adaptive_rules": {"luminaries_factor": 0.9},
                    }
                ],
                "paging": {"limit": 50, "offset": 0, "total": 1},
            }
        }
    )
