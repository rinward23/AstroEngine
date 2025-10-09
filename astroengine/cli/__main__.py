"""Module entry point delegating to the Typer application."""

from __future__ import annotations

from .app import app

__all__ = ["app"]


if __name__ == "__main__":  # pragma: no cover
    app()
