"""Compatibility utilities for the AstroEngine CLI."""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from types import ModuleType
from typing import Final

import click
from typer import Typer
from typer.main import get_command

_CLI_LEGACY_CACHE: ModuleType | None = None
_CLI_LEGACY_ERROR: ModuleNotFoundError | None = None
_SWISSEPH_MODULE: Final[str] = "swisseph"

_APP_CACHE: Typer | None = None


def try_import_cli_legacy() -> ModuleType | None:
    """Try importing :mod:`astroengine.cli_legacy` lazily.

    When the optional Swiss Ephemeris dependency (``pyswisseph``) is not
    installed, importing ``astroengine.cli_legacy`` raises a
    :class:`ModuleNotFoundError`.  In that situation this helper caches the
    failure and returns ``None`` so callers may degrade gracefully (e.g. by
    presenting a helpful message in ``--help`` output).
    """

    global _CLI_LEGACY_CACHE, _CLI_LEGACY_ERROR

    if _CLI_LEGACY_CACHE is not None:
        return _CLI_LEGACY_CACHE
    if _CLI_LEGACY_ERROR is not None:
        return None

    try:
        module = import_module("astroengine.cli_legacy")
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime deps
        if exc.name == _SWISSEPH_MODULE:
            _CLI_LEGACY_ERROR = exc
            return None
        raise

    _CLI_LEGACY_CACHE = module
    return module


def cli_legacy_missing_reason() -> str | None:
    """Return a human readable explanation for the legacy CLI being unavailable."""

    if _CLI_LEGACY_ERROR is None:
        return None
    return (
        "pyswisseph (Swiss Ephemeris) is required for AstroEngine's transit "
        "scanning commands. Install the 'astroengine[ephem]' optional "
        "dependency set or add pyswisseph to your environment."
    )


def require_cli_legacy() -> ModuleType:
    """Return the legacy CLI module or raise a descriptive :class:`RuntimeError`."""

    module = try_import_cli_legacy()
    if module is None:
        reason = cli_legacy_missing_reason() or "pyswisseph is required"
        raise RuntimeError(reason) from _CLI_LEGACY_ERROR
    return module


def _load_app() -> Typer:
    global _APP_CACHE
    if _APP_CACHE is None:
        from .app import app as _app

        _APP_CACHE = _app
    return _APP_CACHE


def build_parser():
    """Return the Click command representing the Typer app (compat shim)."""

    return get_command(_load_app())


def _invoke(argv: Sequence[str] | None = None) -> int:
    command = get_command(_load_app())
    args = list(argv) if argv is not None else None
    try:
        command.main(args=args, prog_name="astroengine", standalone_mode=False)
    except click.exceptions.Exit as exc:
        return int(exc.exit_code or 0)
    except click.ClickException as exc:  # pragma: no cover - click handles presentation
        exc.show()
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Invoke the Typer application (compat shim for legacy entrypoints)."""

    return _invoke(argv)


def console_main() -> None:
    """Invoke :func:`main` and terminate with its exit code."""

    raise SystemExit(main())


def serve_api_entrypoint() -> None:
    """Launch the API server via the Typer façade."""

    import sys

    raise SystemExit(_invoke(["serve-api", *sys.argv[1:]]))


def serve_ui_entrypoint() -> None:
    """Launch the Streamlit UI via the Typer façade."""

    import sys

    raise SystemExit(_invoke(["serve-ui", *sys.argv[1:]]))


def ephe_entrypoint() -> None:
    """Invoke the ephemeris installer via the Typer façade."""

    import sys

    raise SystemExit(_invoke(["ephe", "install", *sys.argv[1:]]))


__all__ = [
    "try_import_cli_legacy",
    "cli_legacy_missing_reason",
    "require_cli_legacy",
    "build_parser",
    "main",
    "console_main",
    "serve_api_entrypoint",
    "serve_ui_entrypoint",
    "ephe_entrypoint",
]
