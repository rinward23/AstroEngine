"""Test-time compatibility patches for third-party libraries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

def _install_hypothesis_patch(module: Any) -> None:
    """Install a timezone-aware `datetimes` helper on the provided module."""

    if getattr(module, "_astroengine_datetimes_patched", False):  # pragma: no cover - idempotent
        return

    original: Callable[..., Any] = module.datetimes

    def _patched_datetimes(*args: Any, **kwargs: Any):
        min_value = kwargs.get("min_value")
        max_value = kwargs.get("max_value")
        tz_strategy = kwargs.get("timezones")
        tzinfo = None

        if isinstance(min_value, datetime) and min_value.tzinfo is not None:
            tzinfo = min_value.tzinfo
            kwargs["min_value"] = min_value.replace(tzinfo=None)
        if isinstance(max_value, datetime) and max_value.tzinfo is not None:
            tzinfo = tzinfo or max_value.tzinfo
            kwargs["max_value"] = max_value.replace(tzinfo=None)

        if tzinfo is not None and tz_strategy is not None:
            strategy = original(*args, **kwargs)
            return strategy.map(lambda dt, _tz=tzinfo: dt.replace(tzinfo=_tz))

        return original(*args, **kwargs)

    module.datetimes = _patched_datetimes
    try:
        from hypothesis.strategies._internal import datetime as _datetime_module  # type: ignore
    except Exception:  # pragma: no cover - internal layout may change
        _datetime_module = None
    else:
        setattr(_datetime_module, "datetimes", _patched_datetimes)
    module._astroengine_datetimes_patched = True


try:
    import hypothesis.strategies as _st
except Exception:  # pragma: no cover - hypothesis optional
    _st = None
else:
    _install_hypothesis_patch(_st)
    _st = None


if _st is None:
    # Hypothesis may not be installed during interpreter bootstrap; register a
    # meta path hook so the patch is applied lazily once the module loads.
    import importlib.abc
    import importlib.machinery
    import sys

    class _HypothesisStrategiesFinder(importlib.abc.MetaPathFinder):  # pragma: no cover - import hook
        def find_spec(self, fullname: str, path: Any, target: Any = None):
            if fullname != "hypothesis.strategies":
                return None
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec is None or spec.loader is None:
                return spec
            loader = spec.loader

            class _PatchedLoader(importlib.abc.Loader):
                def create_module(self, spec):  # pragma: no cover - delegate
                    if hasattr(loader, "create_module"):
                        return loader.create_module(spec)  # type: ignore[attr-defined]
                    return None

                def exec_module(self, module):
                    loader.exec_module(module)
                    _install_hypothesis_patch(module)

            spec.loader = _PatchedLoader()
            return spec

    sys.meta_path.insert(0, _HypothesisStrategiesFinder())
