from app.repo.base import BaseRepo
from app.db.models import Event


class EventRepo(BaseRepo[Event]):
    def __init__(self) -> None:
        super().__init__(Event)
