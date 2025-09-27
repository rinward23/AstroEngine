from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


class LotDefIn(BaseModel):
    name: str
    day: str
    night: str
    description: Optional[str] = ""
    register_flag: bool = Field(default=False, alias="register")
    model_config = ConfigDict(populate_by_name=True)

    @property
    def register(self) -> bool:
        return self.register_flag


class LotsComputeRequest(BaseModel):
    positions: Dict[str, float] = Field(
        ..., description="Symbol → longitude deg; include Asc, Sun, Moon as needed"
    )
    lots: List[str] = Field(default_factory=lambda: ["Fortune", "Spirit"])
    sect: Literal["day", "night"]
    custom_lots: Optional[List[LotDefIn]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "positions": {
                    "Asc": 100.0,
                    "Sun": 10.0,
                    "Moon": 70.0,
                    "Venus": 20.0,
                    "Jupiter": 200.0,
                },
                "lots": ["Fortune", "Spirit", "Eros"],
                "sect": "day",
                "custom_lots": [
                    {
                        "name": "LotOfTest",
                        "day": "Asc + 15 - Sun",
                        "night": "Asc + 15 - Sun",
                        "register": False,
                    }
                ],
            }
        }
    )


class LotsComputeResponse(BaseModel):
    positions: Dict[str, float]
    meta: Dict[str, Any] = Field(default_factory=dict)


class LotDefOut(BaseModel):
    name: str
    day: str
    night: str
    description: str = ""


class LotsCatalogResponse(BaseModel):
    lots: List[LotDefOut]
    meta: Dict[str, Any] = Field(default_factory=dict)

