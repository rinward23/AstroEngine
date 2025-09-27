from app.repo.base import BaseRepo
from app.db.models import ExportJob


class ExportJobRepo(BaseRepo[ExportJob]):
    def __init__(self) -> None:
        super().__init__(ExportJob)
