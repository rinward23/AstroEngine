# >>> AUTO-GEN BEGIN: GeneratedShim v1.0
"""
Deprecation shim for the legacy "generated" package.
This module re-exports from `astroengine` and maps `generated.astroengine`
imports to the real `astroengine` package. Safe to keep for one minor release.
"""
from __future__ import annotations

import sys as _sys
import types as _types
import warnings as _warnings

# Single deprecation nudge on import
_warnings.warn(
    "The 'generated' package is deprecated; use 'astroengine' directly.",
    DeprecationWarning,
    stacklevel=2,
)

# Map submodule path so `import generated.astroengine` resolves to `astroengine`.
try:
    import astroengine as _ae  # noqa: F401

    _sys.modules.setdefault("generated.astroengine", _ae)
except Exception:  # pragma: no cover — leave import errors to normal flow
    pass

# Re-export common public API symbols if available (best-effort, no hard deps)
try:  # noqa: SIM105
    from astroengine import TransitEngine as TransitEngine  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    pass
try:
    from astroengine import (
        TransitScanConfig as TransitScanConfig,  # type: ignore[attr-defined]
    )
except Exception:  # pragma: no cover
    pass
try:
    from astroengine import TransitEvent as TransitEvent  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    pass


# Dynamic attribute forwarding for anything else under astroengine
def __getattr__(name: str):  # pragma: no cover — simple passthrough
    import importlib

    _ae = importlib.import_module("astroengine")
    return getattr(_ae, name)


try:
    import astroengine as _ae_for_all

    __all__ = getattr(_ae_for_all, "__all__", [])  # type: ignore[assignment]
except Exception:  # pragma: no cover
    __all__ = []
# >>> AUTO-GEN END: GeneratedShim v1.0
