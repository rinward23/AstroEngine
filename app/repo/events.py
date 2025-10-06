from app.db.models import Event
from app.repo.base import BaseRepo


class EventRepo(BaseRepo[Event]):
    def __init__(self) -> None:
        super().__init__(Event)
