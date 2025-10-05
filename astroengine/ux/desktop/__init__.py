"""Desktop shell integration for AstroEngine."""

from .app import AstroEngineDesktopApp
from .config import DesktopConfigManager, DesktopConfigModel
from .copilot import DesktopCopilot

__all__ = [
    "AstroEngineDesktopApp",
    "DesktopConfigManager",
    "DesktopConfigModel",
    "DesktopCopilot",
]
