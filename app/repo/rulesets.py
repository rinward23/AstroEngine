from typing import Optional
from sqlalchemy.orm import Session
from app.repo.base import BaseRepo
from app.db.models import RuleSetVersion


class RuleSetRepo(BaseRepo[RuleSetVersion]):
    def __init__(self) -> None:
        super().__init__(RuleSetVersion)

    def get_active(self, db: Session, key: str) -> Optional[RuleSetVersion]:
        return (
            db.query(RuleSetVersion)
            .filter(
                RuleSetVersion.ruleset_key == key,
                RuleSetVersion.is_active.is_(True),
            )
            .order_by(RuleSetVersion.version.desc())
            .first()
        )
