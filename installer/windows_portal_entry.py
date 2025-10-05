"""Entry point that boots the Streamlit portal in the bundled desktop build."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def _resolve_portal_script() -> Path:
    base = _bundle_root()
    candidate = base / "ui" / "streamlit" / "main_portal.py"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Streamlit portal script not found at {candidate}")


def _default_args() -> list[str]:
    script = _resolve_portal_script()
    args = [
        "run",
        str(script),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    port = os.environ.get("ASTROENGINE_PORTAL_PORT")
    if port:
        args.extend(["--server.port", str(port)])
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Launch Streamlit with the bundled main_portal application."""

    args = list(argv or [])
    if not args:
        args = _default_args()
    else:
        args = ["run", str(_resolve_portal_script()), *args]

    try:
        from streamlit.web import cli as stcli
    except Exception as exc:  # pragma: no cover - dependency guard
        raise SystemExit("Streamlit is required to launch the AstroEngine portal.") from exc

    previous = sys.argv
    sys.argv = ["streamlit", *args]
    try:
        stcli.main()
    except SystemExit as exc:  # pragma: no cover - delegated exit codes
        return int(exc.code or 0)
    finally:
        sys.argv = previous
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
