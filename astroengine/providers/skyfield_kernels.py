# >>> AUTO-GEN BEGIN: skyfield-kernel-utils v1.0
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

_DEFAULT_NAMES = ("de440s.bsp", "de421.bsp")
_SEARCH_DIRS: Iterable[Path] = (
    Path.cwd() / "kernels",
    Path.home() / ".skyfield",
    Path.home() / ".astroengine" / "kernels",
)


def find_kernel(preferred: str | None = None) -> Path | None:
    """Return path to an existing SPK kernel if found, else None."""
    candidates = []
    if preferred:
        candidates.append(Path(preferred))
    for d in _SEARCH_DIRS:
        for name in _DEFAULT_NAMES:
            candidates.append(d / name)
    for c in candidates:
        if c.is_file():
            return c
    return None


def ensure_kernel(download: bool = False) -> Path | None:
    """Ensure a kernel is available; optionally download via skyfield Loader.
    No-op if skyfield is not installed or download=False.
    """
    p = find_kernel()
    if p:
        return p
    if not download:
        return None
    try:
        from skyfield.api import Loader  # type: ignore
    except Exception:
        return None
    target_dir = Path.home() / ".skyfield"
    target_dir.mkdir(parents=True, exist_ok=True)
    load = Loader(str(target_dir))
    try:
        eph = load("de440s.bsp")
        return Path(eph.filename)
    except Exception:
        return None


# >>> AUTO-GEN END: skyfield-kernel-utils v1.0
