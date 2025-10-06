from app.db.models import ExportJob
from app.repo.base import BaseRepo


class ExportJobRepo(BaseRepo[ExportJob]):
    def __init__(self) -> None:
        super().__init__(ExportJob)
