from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import sessionmaker

from astroengine.infrastructure.storage.sqlite import apply_default_pragmas

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DB_URL, echo=False, future=True)

if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_configure(dbapi_connection, connection_record):  # pragma: no cover - depends on driver
        apply_default_pragmas(dbapi_connection)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
