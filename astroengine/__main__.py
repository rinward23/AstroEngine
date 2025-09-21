"""Module entry point for `python -m astroengine` delegating to the CLI."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
