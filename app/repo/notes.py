from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChartNote
from app.repo.base import BaseRepo


class NoteRepo(BaseRepo[ChartNote]):
    """Persistence helpers for chart annotations."""

    def __init__(self) -> None:
        super().__init__(ChartNote)

    def list_by_chart(self, db: Session, chart_id: int) -> Iterable[ChartNote]:
        statement = (
            select(self.model)
            .where(self.model.chart_id == chart_id)
            .order_by(self.model.created_at.desc())
        )
        return list(db.execute(statement).scalars())

    def list_all(self, db: Session) -> Iterable[ChartNote]:
        statement = select(self.model).order_by(self.model.created_at.desc())
        return list(db.execute(statement).scalars())
