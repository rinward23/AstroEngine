from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import sessionmaker


def _postgres_engine_kwargs() -> dict[str, Any]:
    """Return connection pooling and prepared statement settings for Postgres."""

    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_POOL_MAX_OVERFLOW", "10"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    batch_size = int(os.getenv("DB_EXECUTEMANY_BATCH_SIZE", "500"))

    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_timeout": pool_timeout,
        "pool_recycle": pool_recycle,
        "pool_pre_ping": True,
        "executemany_mode": "values_plus_batch",
        "executemany_parameters": {"batch_size": batch_size},
    }


def _enrich_postgres_url(url: URL) -> URL:
    """Attach prepared statement configuration hints to a Postgres URL."""

    query = dict(url.query)
    prepare_threshold = os.getenv("PG_PREPARE_THRESHOLD") or "1"
    prepared_cache = os.getenv("PG_PREPARED_STATEMENT_CACHE_SIZE") or "256"
    query.setdefault("prepare_threshold", prepare_threshold)
    query.setdefault("prepared_statement_cache_size", prepared_cache)
    return url.set(query=query)


def build_engine(db_url: str | URL | None = None) -> Engine:
    """Create a SQLAlchemy engine configured from the provided or default URL."""

    resolved_url = make_url(str(db_url or os.getenv("DATABASE_URL", "sqlite:///./dev.db")))
    engine_kwargs: dict[str, Any] = {"echo": False, "future": True}

    if resolved_url.get_backend_name() in {"postgresql", "postgres"}:
        engine_kwargs.update(_postgres_engine_kwargs())
        resolved_url = _enrich_postgres_url(resolved_url)

    engine = create_engine(resolved_url, **engine_kwargs)

    if resolved_url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _sqlite_configure(dbapi_connection, connection_record):  # pragma: no cover - depends on driver
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
            finally:
                cursor.close()

    return engine


DB_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = build_engine(DB_URL)

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
