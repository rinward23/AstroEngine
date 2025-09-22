"""Utility helpers shared by Swiss ephemeris adapters."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

__all__ = ["get_se_ephe_path"]

_ENV_KEYS: tuple[str, ...] = ("SE_EPHE_PATH", "SWISSEPH_PATH", "SE_PATH")


def _first_env(paths: Iterable[str]) -> str | None:
    for key in paths:
        value = os.getenv(key)
        if value:
            candidate = Path(value).expanduser()
            return str(candidate)
    return None


def get_se_ephe_path(default: str | None = None) -> str | None:
    """Return the configured Swiss ephemeris directory if present."""

    env_path = _first_env(_ENV_KEYS)
    if env_path:
        return env_path
    if default:
        return str(Path(default).expanduser())
    return None
