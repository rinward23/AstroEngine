# >>> AUTO-GEN BEGIN: Ephemeris Utils v1.1
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

__all__ = ["DEFAULT_EPHE_PATHS", "get_se_ephe_path"]

DEFAULT_EPHE_PATHS: tuple[Path, ...] = (
    Path.home() / ".sweph" / "ephe",
    Path.home() / ".sweph",
    Path("/usr/share/sweph"),
    Path("/usr/share/libswisseph"),
)


def _iter_candidates(extra: Iterable[str | os.PathLike[str]] | None) -> Iterable[Path]:
    if extra:
        for item in extra:
            candidate = Path(item).expanduser()
            if candidate:
                yield candidate
    for default in DEFAULT_EPHE_PATHS:
        yield default


def get_se_ephe_path(
    extra_paths: Iterable[str | os.PathLike[str]] | None = None,
) -> str | None:
    """Return a usable Swiss Ephemeris directory if present."""

    env_path = os.getenv("SE_EPHE_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_dir():
            return str(candidate)

    for candidate in _iter_candidates(extra_paths):
        if candidate.is_dir():
            return str(candidate)
    return None

# >>> AUTO-GEN END: Ephemeris Utils v1.1
