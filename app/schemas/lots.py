from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LotDefIn(BaseModel):
    name: str
    day: str
    night: str
    description: str | None = ""
    register_flag: bool = Field(default=False, alias="register")
    model_config = ConfigDict(populate_by_name=True)

    @property
    def register(self) -> bool:
        return self.register_flag


class LotsComputeRequest(BaseModel):
    positions: dict[str, float] = Field(
        ..., description="Symbol → longitude deg; include Asc, Sun, Moon as needed"
    )
    lots: list[str] = Field(default_factory=lambda: ["Fortune", "Spirit"])
    sect: Literal["day", "night"]
    custom_lots: list[LotDefIn] | None = None

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
    positions: dict[str, float]
    meta: dict[str, Any] = Field(default_factory=dict)


class LotDefOut(BaseModel):
    name: str
    day: str
    night: str
    description: str = ""


class LotsCatalogResponse(BaseModel):
    lots: list[LotDefOut]
    meta: dict[str, Any] = Field(default_factory=dict)

