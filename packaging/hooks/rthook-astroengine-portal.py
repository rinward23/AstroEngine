"""Configure environment variables for the bundled AstroEngine portal."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _ensure_dir(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def _configure_user_space(root: Path) -> None:
    local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    user_root = _ensure_dir(local_appdata / "AstroEngine")
    os.environ.setdefault("ASTROENGINE_HOME", str(user_root))
    os.environ.setdefault("ASTROENGINE_DATA_ROOT", str(_ensure_dir(user_root / "data")))
    _ensure_dir(user_root / "logs")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "0")


def _configure_ephemeris(root: Path) -> None:
    candidate = root / "resources" / "ephemeris"
    if candidate.exists():
        os.environ.setdefault("SE_EPHE_PATH", str(candidate))


def configure_environment() -> None:
    root = _bundle_root()
    _configure_ephemeris(root)
    _configure_user_space(root)
    portal_script = root / "ui" / "streamlit" / "main_portal.py"
    os.environ.setdefault("ASTROENGINE_PORTAL_SCRIPT", str(portal_script))


configure_environment()
