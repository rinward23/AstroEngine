from typing import Iterable
from sqlalchemy.orm import Session
from app.repo.base import BaseRepo
from app.db.models import Chart, Event


class ChartRepo(BaseRepo[Chart]):
    def __init__(self) -> None:
        super().__init__(Chart)

    def list_events(self, db: Session, chart_id: int) -> Iterable[Event]:
        ch = self.get(db, chart_id)
        return ch.events if ch else []
