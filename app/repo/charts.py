from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models import Chart, Event, _normalize_tags
from app.repo.base import BaseRepo


class ChartRepo(BaseRepo[Chart]):
    """Repository helpers for :class:`~app.db.models.Chart`."""

    def __init__(self) -> None:
        super().__init__(Chart)

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    def get(
        self, db: Session, id: int, *, include_deleted: bool = False
    ) -> Chart | None:
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return db.execute(stmt).scalar_one_or_none()

    def list(self, db: Session, limit: int = 100, offset: int = 0) -> list[Chart]:
        stmt = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars())

    def list_deleted(self, db: Session, limit: int = 100, offset: int = 0) -> list[Chart]:
        stmt = (
            select(self.model)
            .where(self.model.deleted_at.is_not(None))
            .order_by(self.model.deleted_at.desc(), self.model.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars())

    def delete(self, db: Session, id: int) -> None:  # type: ignore[override]
        self.soft_delete(db, id)

    def soft_delete(self, db: Session, chart_id: int) -> Chart | None:
        chart = self.get(db, chart_id)
        if chart is None:
            return None
        chart.deleted_at = datetime.now(timezone.utc)
        db.flush()
        return chart

    def restore(self, db: Session, chart_id: int) -> Chart | None:
        chart = self.get(db, chart_id, include_deleted=True)
        if chart is None or chart.deleted_at is None:
            return None
        chart.deleted_at = None
        db.flush()
        return chart

    def update_tags(
        self, db: Session, chart_id: int, tags: Sequence[str]
    ) -> Chart:
        chart = self.get(db, chart_id, include_deleted=True)
        if chart is None:
            raise ValueError(f"Chart {chart_id} not found")
        chart.tags = _normalize_tags(tags)
        chart.updated_at = datetime.now(timezone.utc)
        db.flush()
        return chart

    def list_events(self, db: Session, chart_id: int) -> Iterable[Event]:
        chart = self.get(db, chart_id)
        return chart.events if chart else []

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------
    def search(
        self,
        db: Session,
        *,
        query: str | None = None,
        tags: Sequence[str] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Chart]:
        stmt = select(self.model)
        conditions = []
        if not include_deleted:
            conditions.append(self.model.deleted_at.is_(None))
        if query:
            pattern = f"%{query.lower()}%"
            conditions.append(func.lower(self.model.chart_key).like(pattern))
        if created_from:
            conditions.append(self.model.created_at >= created_from)
        if created_to:
            conditions.append(self.model.created_at <= created_to)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = (
            stmt.order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        results = list(db.execute(stmt).scalars())
        if tags:
            normalized = _normalize_tags(tags)
            if normalized:
                results = [
                    chart
                    for chart in results
                    if all(tag in chart.tags for tag in normalized)
                ]
        return results


__all__ = ["ChartRepo"]

