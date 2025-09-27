"""SQLAlchemy declarative base for AstroEngine application models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class used by all ORM models in the app package."""

    pass
