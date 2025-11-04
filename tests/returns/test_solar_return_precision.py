from __future__ import annotations

from datetime import UTC, datetime

import pytest

try:
    from astroengine.core.time import to_tt
except ImportError as exc:  # pragma: no cover - optional dependency gating
    to_tt = None  # type: ignore[assignment]
    _CORE_IMPORT_ERROR = exc
else:
    _CORE_IMPORT_ERROR = None

from astroengine.engine.returns import find_return_instant, guess_window
from astroengine.engine.returns._codes import resolve_body_code

try:
    from astroengine.ephemeris import EphemerisAdapter
except ImportError as exc:  # pragma: no cover - optional dependency gating
    EphemerisAdapter = None  # type: ignore[assignment]
    _EPHEMERIS_IMPORT_ERROR = exc
else:
    _EPHEMERIS_IMPORT_ERROR = None


def _wrap(delta: float) -> float:
    return ((delta + 180.0) % 360.0) - 180.0


@pytest.mark.swiss
def test_solar_return_precision() -> None:
    if to_tt is None:
        pytest.skip(f"to_tt unavailable: {_CORE_IMPORT_ERROR}")
    if EphemerisAdapter is None:
        pytest.skip(f"EphemerisAdapter unavailable: {_EPHEMERIS_IMPORT_ERROR}")
    adapter = EphemerisAdapter()
    natal_dt = datetime(1990, 5, 4, 12, 30, tzinfo=UTC)
    code = resolve_body_code("Sun").code
    natal_conv = to_tt(natal_dt)
    natal_lon = adapter.sample(code, natal_conv).longitude % 360.0

    around = datetime(2026, 5, 4, 12, 30, tzinfo=UTC)
    window = guess_window("Sun", None, around)
    instant = find_return_instant(adapter, "Sun", natal_lon, window)

    assert instant.status == "ok"
    conv_exact = to_tt(instant.exact_time)
    lon_exact = adapter.sample(code, conv_exact).longitude % 360.0
    delta = abs(_wrap(lon_exact - natal_lon))
    assert delta * 3600.0 < 0.5
    assert instant.achieved_tolerance_seconds <= 0.3
