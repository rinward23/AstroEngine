from app.repo.base import BaseRepo
from app.db.models import OrbPolicy


class OrbPolicyRepo(BaseRepo[OrbPolicy]):
    def __init__(self) -> None:
        super().__init__(OrbPolicy)
