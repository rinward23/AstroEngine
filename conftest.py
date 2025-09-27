"""Pytest configuration for AstroEngine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


def _install_hypothesis_patch() -> None:
    try:
        import hypothesis.strategies as _st
    except Exception:  # pragma: no cover - hypothesis optional
        return

    if getattr(_st, "_astroengine_datetimes_patched", False):  # pragma: no cover - idempotent
        return

    original: Callable[..., Any] = _st.datetimes

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

    _st.datetimes = _patched_datetimes
    try:
        from hypothesis.strategies._internal import datetime as _dt_mod  # type: ignore
    except Exception:  # pragma: no cover - internal layout may change
        pass
    else:
        setattr(_dt_mod, "datetimes", _patched_datetimes)
    _st._astroengine_datetimes_patched = True


_install_hypothesis_patch()

