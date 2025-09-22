"""Swiss ephemeris path discovery helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Iterator

from ..infrastructure.paths import datasets_dir

__all__ = [
    "DEFAULT_ENV_KEYS",
    "DEFAULT_SUBDIRS",
    "iter_candidate_paths",
    "get_se_ephe_path",
]

DEFAULT_ENV_KEYS: tuple[str, ...] = (
    "SE_EPHE_PATH",
    "SWE_EPH_PATH",
    "ASTROENGINE_SE_EPHE_PATH",
    "ASTROENGINE_EPHEMERIS_PATH",
)
"""Environment variables checked (in order) for Swiss ephemeris paths."""

DEFAULT_SUBDIRS: tuple[str, ...] = ("ephe", "sefstars")
"""Common Swiss ephemeris sub-directories to validate when probing paths."""

_DATASETS_ROOT = datasets_dir()
_STUB_DIR = _DATASETS_ROOT / "swisseph_stub"

_DEFAULT_HINTS: tuple[Path, ...] = (
    Path.home() / ".sweph",
    Path("/usr/share/sweph"),
    Path("/usr/share/libswisseph"),
)


def _first_env(keys: Iterable[str]) -> str | None:
    """Return the first non-empty environment variable value from ``keys``."""

    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _ensure_dir(path: os.PathLike[str] | str | None) -> str | None:
    """Expand ``path`` to an absolute directory string when it exists."""

    if not path:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_dir():
        return str(candidate)
    return None


def iter_candidate_paths(
    default: str | os.PathLike[str] | None = None,
) -> Iterator[str]:
    """Yield Swiss ephemeris path candidates in priority order."""

    seen: set[str] = set()

    # Caller-provided default path
    default_dir = _ensure_dir(default)
    if default_dir and default_dir not in seen:
        seen.add(default_dir)
        yield default_dir

    # Repository stub directory keeps tests deterministic
    stub_dir = _ensure_dir(_STUB_DIR)
    if stub_dir and stub_dir not in seen:
        seen.add(stub_dir)
        yield stub_dir

    # Environment-provided data roots may include bundled ephemeris data
    data_root = _ensure_dir(os.environ.get("ASTROENGINE_DATA_ROOT"))
    if data_root:
        for sub in DEFAULT_SUBDIRS + ("",):
            candidate_path = Path(data_root) / sub if sub else Path(data_root)
            candidate = _ensure_dir(candidate_path)
            if candidate and candidate not in seen:
                seen.add(candidate)
                yield candidate

    # OS-level default search paths
    for hint in _DEFAULT_HINTS:
        candidate = _ensure_dir(hint)
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def get_se_ephe_path(default: str | os.PathLike[str] | None = None) -> str | None:
    """Return the Swiss ephemeris path or ``None`` when unavailable."""

    env_path = _ensure_dir(_first_env(DEFAULT_ENV_KEYS))
    if env_path:
        return env_path

    for candidate in iter_candidate_paths(default):
        return candidate
    return None
