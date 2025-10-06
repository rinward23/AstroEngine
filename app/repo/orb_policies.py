from app.db.models import OrbPolicy
from app.repo.base import BaseRepo


class OrbPolicyRepo(BaseRepo[OrbPolicy]):
    def __init__(self) -> None:
        super().__init__(OrbPolicy)
