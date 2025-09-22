
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable



    env_path = _first_env(_ENV_KEYS)
    if env_path:
        return env_path
    if default:
        return str(Path(default).expanduser())
    return None
