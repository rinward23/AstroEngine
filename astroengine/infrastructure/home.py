# >>> AUTO-GEN BEGIN: infra-home v1.0
from __future__ import annotations
from pathlib import Path
import os

_DEF_HOME = Path.home() / ".astroengine"


def ae_home() -> Path:
    p = os.environ.get("ASTROENGINE_HOME")
    return Path(p).expanduser() if p else _DEF_HOME
# >>> AUTO-GEN END: infra-home v1.0
