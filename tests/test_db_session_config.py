from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.engine import URL


@pytest.fixture
def session_module(monkeypatch):
    """Provide an isolated import of ``app.db.session`` for each test."""

    import app.db.session as session

    yield session

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_POOL_TIMEOUT", raising=False)
    monkeypatch.delenv("DB_POOL_RECYCLE", raising=False)
    monkeypatch.delenv("DB_EXECUTEMANY_BATCH_SIZE", raising=False)
    monkeypatch.delenv("PG_PREPARE_THRESHOLD", raising=False)
    monkeypatch.delenv("PG_PREPARED_STATEMENT_CACHE_SIZE", raising=False)
    importlib.reload(session)


def test_postgres_engine_uses_pooling_and_prepared_statements(monkeypatch, session_module):
    """Ensure Postgres engines are built with pooling and prepared statement hints."""

    captured: dict[str, object] = {}

    def fake_create_engine(url, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["kwargs"] = kwargs
        return SimpleNamespace(url=url)

    monkeypatch.setenv("DB_POOL_SIZE", "9")
    monkeypatch.setenv("DB_POOL_MAX_OVERFLOW", "2")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "15")
    monkeypatch.setenv("DB_POOL_RECYCLE", "600")
    monkeypatch.setenv("DB_EXECUTEMANY_BATCH_SIZE", "123")
    monkeypatch.setenv("PG_PREPARE_THRESHOLD", "2")
    monkeypatch.setenv("PG_PREPARED_STATEMENT_CACHE_SIZE", "300")

    monkeypatch.setattr(session_module, "create_engine", fake_create_engine)

    engine = session_module.build_engine("postgresql+psycopg://user:pass@localhost/dbname")

    assert isinstance(engine, SimpleNamespace)

    kwargs = cast(dict[str, Any], captured["kwargs"])
    assert kwargs["pool_size"] == 9
    assert kwargs["max_overflow"] == 2
    assert kwargs["pool_timeout"] == 15
    assert kwargs["pool_recycle"] == 600
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["executemany_mode"] == "values_plus_batch"
    assert kwargs["executemany_parameters"] == {"batch_size": 123}

    url = cast(URL, captured["url"])
    assert url.query["prepare_threshold"] == "2"
    assert url.query["prepared_statement_cache_size"] == "300"
