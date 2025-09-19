# >>> AUTO-GEN BEGIN: AstroEngine Swiss Ephemeris Smoketest v1.0
#!/usr/bin/env python
"""Minimal import check for Swiss Ephemeris and core deps."""
import importlib
import sys

missing = []


def _ensure_module(name: str) -> None:
    """Attempt to import *name* and capture any exception."""

    try:
        importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - exercised via smoketest script
        missing.append((name, str(exc)))


def _ensure_any(candidates: list[str]) -> None:
    """Import the first available module from *candidates*."""

    errors = []
    for module in candidates:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - exercised via smoketest script
            errors.append(f"{module}: {exc}")
        else:
            return

    missing.append((candidates[0], "; ".join(errors)))


_ensure_any(["swisseph", "pyswisseph"])
for module_name in ["numpy", "pandas", "pyarrow", "pluggy", "yaml"]:
    _ensure_module(module_name)

if missing:
    print("[smoketest] Missing/failed imports:")
    for module_name, error in missing:
        print(f"  - {module_name}: {error}")
    sys.exit(1)
else:
    print("[smoketest] All core imports present.")

# >>> AUTO-GEN END: AstroEngine Swiss Ephemeris Smoketest v1.0
