"""Feature flag helpers governing modality registration and exposure."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import FrozenSet, Tuple

# Canonical modality names that are fully implemented and safe to expose by default.
IMPLEMENTED_MODALITIES: FrozenSet[str] = frozenset(
    {
        "lunations",
        "eclipses",
        "stations",
        "progressions",
        "directions",
        "returns",
        "profections",
        "timelords",
    }
)

# Experimental or unfinished modalities. They require an explicit opt-in.
EXPERIMENTAL_MODALITIES: FrozenSet[str] = frozenset(
    {
        "prog-aspects",
        "dir-aspects",
    }
)

_ENVIRONMENT_FLAG = "ASTROENGINE_EXPERIMENTAL_MODALITIES"


def _normalize(name: str) -> str:
    return str(name or "").strip().lower()


@lru_cache(maxsize=1)
def experimental_modalities_from_env() -> FrozenSet[str]:
    """Return experimental modalities enabled via environment variable."""

    raw = os.getenv(_ENVIRONMENT_FLAG, "")
    if not raw:
        return frozenset()
    entries = {
        _normalize(token)
        for chunk in raw.split(",")
        for token in chunk.split()
        if _normalize(token)
    }
    return frozenset(entry for entry in entries if entry in EXPERIMENTAL_MODALITIES)


def is_enabled(name: str, *, experimental: bool = False) -> bool:
    """Return ``True`` when ``name`` is an enabled modality.

    Parameters
    ----------
    name:
        Candidate modality identifier. Comparison is case-insensitive.
    experimental:
        When ``True`` the function treats every entry in
        :data:`EXPERIMENTAL_MODALITIES` as enabled regardless of the
        environment toggle. This is useful for programmatic opt-ins.
    """

    key = _normalize(name)
    if not key:
        return False
    if key in IMPLEMENTED_MODALITIES:
        return True
    if key in EXPERIMENTAL_MODALITIES:
        return experimental or key in experimental_modalities_from_env()
    return False


def available_modalities(*, include_experimental: bool = False) -> Tuple[str, ...]:
    """Return a sorted tuple of modality names.

    Parameters
    ----------
    include_experimental:
        When ``True`` experimental modalities are included in the output even if
        the environment toggle is absent. This mirrors how UIs may surface
        opt-in checkboxes while keeping them disabled by default.
    """

    names: set[str] = set(IMPLEMENTED_MODALITIES)
    if include_experimental:
        names.update(EXPERIMENTAL_MODALITIES)
    return tuple(sorted(names))


__all__ = [
    "IMPLEMENTED_MODALITIES",
    "EXPERIMENTAL_MODALITIES",
    "available_modalities",
    "experimental_modalities_from_env",
    "is_enabled",
]
