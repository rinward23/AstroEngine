from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
GENERATED_ROOT = PROJECT_ROOT / "generated"
GENERATED_STR = str(GENERATED_ROOT)


def _ensure_repo_package() -> None:
    while PROJECT_ROOT_STR in sys.path:
        sys.path.remove(PROJECT_ROOT_STR)
    sys.path.insert(0, PROJECT_ROOT_STR)
    for candidate in (GENERATED_STR, "generated"):
        while candidate in sys.path:
            sys.path.remove(candidate)
        sys.path.append(candidate)

    module = sys.modules.get("astroengine")
    if module is not None:
        module_file = getattr(module, "__file__", "") or ""
        if module_file and str(GENERATED_ROOT) in module_file:
            for key in list(sys.modules):
                if key == "astroengine" or key.startswith("astroengine."):
                    sys.modules.pop(key, None)
            module = None
    if module is None:
        importlib.invalidate_caches()
    try:
        module = importlib.import_module("astroengine")
    except ModuleNotFoundError:
        return
    module_file = getattr(module, "__file__", "") or ""
    if module_file and str(GENERATED_ROOT) in module_file:
        for key in list(sys.modules):
            if key == "astroengine" or key.startswith("astroengine."):
                sys.modules.pop(key, None)
        importlib.invalidate_caches()
        importlib.import_module("astroengine")


_ensure_repo_package()

# >>> AUTO-GEN BEGIN: swiss availability gating v1.0
import os
import pytest


def _have_pyswisseph() -> bool:
    try:
        import swisseph as _swe  # noqa: F401
        return True
    except Exception:
        return False


def _have_ephe_path() -> bool:
    p = os.getenv("SE_EPHE_PATH")
    return bool(p and os.path.isdir(p))


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked 'swiss' unless pyswisseph + ephemeris path are available."""
    swiss_missing = not _have_pyswisseph() or not _have_ephe_path()
    if not swiss_missing:
        return
    skip_swiss = pytest.mark.skip(reason="Swiss Ephemeris unavailable (no pyswisseph or SE_EPHE_PATH).")
    for item in items:
        if "swiss" in item.keywords:
            item.add_marker(skip_swiss)
# >>> AUTO-GEN END: swiss availability gating v1.0


@pytest.fixture(autouse=True)
def _restore_repo_package() -> None:
    _ensure_repo_package()
    yield
    _ensure_repo_package()
