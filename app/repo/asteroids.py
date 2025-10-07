from app.db.models import AsteroidMeta
from app.repo.base import BaseRepo


class AsteroidRepo(BaseRepo[AsteroidMeta]):
    def __init__(self) -> None:
        super().__init__(AsteroidMeta)
