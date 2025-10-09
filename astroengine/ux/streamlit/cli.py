"""Launch helpers for the AstroEngine Streamlit dashboards."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from astroengine.boot.logging import configure_logging

DEFAULT_APP_PATH = (
    Path(__file__).resolve().parents[3]
    / "ui"
    / "streamlit"
    / "pages"
    / "01_Aspect_Search.py"
)


def _resolve_app_path(override: str | None) -> Path:
    """Return the Streamlit app path, validating overrides when provided."""

    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if not candidate.exists():
            raise FileNotFoundError(f"Streamlit app not found: {candidate}")
        return candidate

    if DEFAULT_APP_PATH.exists():
        return DEFAULT_APP_PATH

    raise FileNotFoundError(
        "Default Aspect Search app is unavailable. Pass an explicit path to the Streamlit script."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Invoke the bundled Streamlit UI via ``astroengine-streamlit``."""

    configure_logging()

    args = list(argv if argv is not None else sys.argv[1:])
    app_override: str | None = None
    if args and not args[0].startswith("-"):
        app_override = args.pop(0)

    try:
        script_path = _resolve_app_path(app_override)
    except FileNotFoundError as exc:  # pragma: no cover - defensive user guidance
        raise SystemExit(str(exc)) from exc

    try:
        from streamlit.web import cli as stcli
    except Exception as exc:  # pragma: no cover - dependency guard
        raise SystemExit(
            "Streamlit is not installed. Install astroengine[streamlit] or add streamlit to your environment."
        ) from exc

    previous_argv = sys.argv
    sys.argv = ["streamlit", "run", str(script_path), *args]
    try:
        stcli.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    finally:
        sys.argv = previous_argv
    return 0


__all__ = ["DEFAULT_APP_PATH", "main"]

