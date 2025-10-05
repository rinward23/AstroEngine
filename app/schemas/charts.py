from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChartSummary(BaseModel):
    id: int
    chart_key: str
    profile_key: str
    kind: str | None = None
    dt_utc: datetime | None = None
    location_name: str | None = None
    module: str
    submodule: str | None = None
    channel: str
    subchannel: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ChartTagsUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)


__all__ = ["ChartSummary", "ChartTagsUpdate"]

