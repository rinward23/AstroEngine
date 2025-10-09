"""Runtime Swiss ephemeris initialization helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from astroengine.ephemeris.swe import swe
from astroengine.ephemeris.utils import get_se_ephe_path

LOG = logging.getLogger(__name__)

_EPHE_SUFFIXES: tuple[str, ...] = (".se1", ".se2", ".se3", ".se4", ".se5")

_DEFAULT_FLAGS: int | None = None


def _normalize_path(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_dir():
        return str(candidate)
    return None


def _iter_files(root: Path) -> Iterable[Path]:
    try:
        yield from root.iterdir()
    except OSError:
        return


def has_ephemeris_files(path: str | None = None) -> bool:
    """Return ``True`` when Swiss ``.se1``-``.se5`` files exist."""

    candidate = _normalize_path(path)
    if candidate is None:
        candidate = get_se_ephe_path()
    if not candidate:
        return False

    root = Path(candidate)
    if not root.is_dir():
        return False

    suffixes = set()
    for entry in _iter_files(root):
        if not entry.is_file():
            continue
        suffix = entry.suffix.lower()
        if suffix in _EPHE_SUFFIXES:
            suffixes.add(suffix)
    return bool(suffixes)


def init_ephe(
    path: str | None = None, *, force: bool = False, prefer_moshier: bool = False
) -> int:
    """Initialise Swiss ephemeris path and return default flags."""

    global _DEFAULT_FLAGS

    if _DEFAULT_FLAGS is not None and not force and path is None and not prefer_moshier:
        return _DEFAULT_FLAGS

    resolved = _normalize_path(path) or get_se_ephe_path()

    swe_module = swe()

    mode = "moshier"
    if prefer_moshier:
        swe_module.set_ephe_path(None)
        flags = int(getattr(swe_module, "FLG_MOSEPH"))
    elif resolved and has_ephemeris_files(resolved):
        swe_module.set_ephe_path(resolved)
        flags = int(getattr(swe_module, "FLG_SWIEPH"))
        mode = "swiss"
    else:
        swe_module.set_ephe_path(None)
        flags = int(getattr(swe_module, "FLG_MOSEPH"))
    if prefer_moshier and resolved:
        LOG.debug(
            "Swiss ephemeris path '%s' supplied but Moshier fallback requested", resolved
        )

    detail = resolved or "(auto)"
    if mode == "moshier" and resolved and not prefer_moshier:
        LOG.info(
            "Ephemeris runtime mode: %s (path=%s - Swiss data missing)", mode, detail
        )
    else:
        LOG.info("Ephemeris runtime mode: %s (path=%s)", mode, detail)

    if path is None or force or prefer_moshier:
        _DEFAULT_FLAGS = flags

    return flags


__all__ = ["has_ephemeris_files", "init_ephe"]
