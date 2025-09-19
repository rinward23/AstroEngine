"""Entry point to expose `python -m astroengine` CLI."""
from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
