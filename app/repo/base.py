from __future__ import annotations
from typing import Generic, TypeVar, Type, Optional, Iterable
from sqlalchemy.orm import Session

T = TypeVar("T")

class BaseRepo(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    def create(self, db: Session, **kwargs) -> T:
        obj = self.model(**kwargs)
        db.add(obj)
        db.flush()  # assign PK
        return obj

    def get(self, db: Session, id: int) -> Optional[T]:
        return db.get(self.model, id)

    def list(self, db: Session, limit: int = 100, offset: int = 0) -> Iterable[T]:
        return db.query(self.model).offset(offset).limit(limit).all()

    def update(self, db: Session, id: int, **kwargs) -> T:
        obj = self.get(db, id)
        if not obj:
            raise ValueError(f"{self.model.__name__} {id} not found")
        for k, v in kwargs.items():
            setattr(obj, k, v)
        db.flush()
        return obj

    def delete(self, db: Session, id: int) -> None:
        obj = self.get(db, id)
        if not obj:
            return
        db.delete(obj)
        db.flush()
