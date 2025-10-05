"""Desktop shell integration for AstroEngine."""

from .app import AstroEngineDesktopApp
from .config import DesktopConfigManager, DesktopConfigModel
from .copilot import DesktopCopilot
from .wizard import run_first_run_wizard, should_run_wizard

__all__ = [
    "AstroEngineDesktopApp",
    "DesktopConfigManager",
    "DesktopConfigModel",
    "DesktopCopilot",
    "run_first_run_wizard",
    "should_run_wizard",
]
