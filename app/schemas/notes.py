from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    chart_id: int
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    pass


class NoteOut(NoteBase):
    id: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
