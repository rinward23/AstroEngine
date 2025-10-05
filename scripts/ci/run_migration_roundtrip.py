"""CI helper to validate Alembic migrations across multiple backends."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Sequence

from alembic import command
from alembic.config import Config


def _run_roundtrip(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@contextlib.contextmanager
def _sqlite_url() -> Iterator[str]:
    with tempfile.TemporaryDirectory(prefix="astroengine-migrations-") as tmpdir:
        path = Path(tmpdir) / "roundtrip.db"
        yield f"sqlite:///{path}"


@contextlib.contextmanager
def _postgres_url(image: str) -> Iterator[str]:
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(image) as container:
        yield container.get_connection_url()


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backends",
        nargs="*",
        default=("sqlite", "postgres"),
        choices=("sqlite", "postgres"),
        help="Database backends to validate.",
    )
    parser.add_argument(
        "--postgres-image",
        default="postgres:16-alpine",
        help="Docker image used for the Postgres test container.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    for backend in args.backends:
        if backend == "sqlite":
            with _sqlite_url() as url:
                _run_roundtrip(url)
        elif backend == "postgres":
            with _postgres_url(args.postgres_image) as url:
                _run_roundtrip(url)
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported backend: {backend}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
