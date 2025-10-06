
from sqlalchemy.orm import Session

from app.db.models import RuleSetVersion
from app.repo.base import BaseRepo


class RuleSetRepo(BaseRepo[RuleSetVersion]):
    def __init__(self) -> None:
        super().__init__(RuleSetVersion)

    def get_active(self, db: Session, key: str) -> RuleSetVersion | None:
        return (
            db.query(RuleSetVersion)
            .filter(
                RuleSetVersion.ruleset_key == key,
                RuleSetVersion.is_active.is_(True),
            )
            .order_by(RuleSetVersion.version.desc())
            .first()
        )
