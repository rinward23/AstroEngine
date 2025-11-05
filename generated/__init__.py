# >>> AUTO-GEN BEGIN: GeneratedShim v1.0
"""
Deprecation shim for the legacy "generated" package.
This module re-exports from `astroengine` and maps `generated.astroengine`
imports to the real `astroengine` package. Safe to keep for one minor release.
"""
from __future__ import annotations

import logging as _logging
import sys as _sys
import warnings as _warnings

_LOG = _logging.getLogger(__name__)

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
except Exception as exc:  # pragma: no cover — leave import errors to normal flow
    _LOG.debug("Deferred astroengine import for generated shim: %s", exc)

# Re-export common public API symbols if available (best-effort, no hard deps)
try:  # noqa: SIM105
    from astroengine.transits import TransitEngine as TransitEngine
except Exception as exc:  # pragma: no cover
    _LOG.debug("TransitEngine not available for generated shim: %s", exc)
try:
    from astroengine.transits import TransitScanConfig as TransitScanConfig
except Exception as exc:  # pragma: no cover
    _LOG.debug("TransitScanConfig not available for generated shim: %s", exc)
try:
    from astroengine.transits import TransitEvent as TransitEvent
except Exception as exc:  # pragma: no cover
    _LOG.debug("TransitEvent not available for generated shim: %s", exc)


# Dynamic attribute forwarding for anything else under astroengine
def __getattr__(name: str):  # pragma: no cover — simple passthrough
    import importlib

    _ae = importlib.import_module("astroengine")
    return getattr(_ae, name)


try:
    import astroengine as _ae_for_all

    __all__ = getattr(_ae_for_all, "__all__", [])  # type: ignore[assignment]
except Exception as exc:  # pragma: no cover
    _LOG.debug("Unable to derive __all__ for generated shim: %s", exc)
    __all__ = []
# >>> AUTO-GEN END: GeneratedShim v1.0
