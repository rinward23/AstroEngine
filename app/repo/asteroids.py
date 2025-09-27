from app.repo.base import BaseRepo
from app.db.models import AsteroidMeta


class AsteroidRepo(BaseRepo[AsteroidMeta]):
    def __init__(self) -> None:
        super().__init__(AsteroidMeta)
