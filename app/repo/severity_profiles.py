from app.repo.base import BaseRepo
from app.db.models import SeverityProfile


class SeverityProfileRepo(BaseRepo[SeverityProfile]):
    def __init__(self) -> None:
        super().__init__(SeverityProfile)
