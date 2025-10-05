"""Alembic environment configuring AstroEngine Plus metadata."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.db import models  # noqa: F401 - ensure models are registered with the metadata

DEFAULT_DB_URL = "sqlite:///./dev.db"

config = context.config
configured_url = config.get_main_option("sqlalchemy.url") or DEFAULT_DB_URL
database_url = os.getenv("DATABASE_URL", configured_url if "${" not in configured_url else DEFAULT_DB_URL)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live connection."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        metadata=target_metadata,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a connection to the configured database."""

    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            metadata=target_metadata,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations() -> None:
    """Entry point invoked by Alembic based on execution mode."""

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


run_migrations()
