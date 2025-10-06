from app.db.models import SeverityProfile
from app.repo.base import BaseRepo


class SeverityProfileRepo(BaseRepo[SeverityProfile]):
    def __init__(self) -> None:
        super().__init__(SeverityProfile)
