from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph required for precise return calculations.",
)

from astroengine.analysis import aries_ingress_year, lunar_return_datetimes, solar_return_datetime


def _days_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 86400.0


def test_solar_return_handles_year_boundary() -> None:
    natal = datetime(2000, 1, 1, 0, 0, tzinfo=UTC)
    result = solar_return_datetime(natal, "UTC", 2024)

    assert result.tzinfo is not None
    approx = datetime(2024, natal.month, natal.day, natal.hour, natal.minute, tzinfo=UTC)
    assert _days_between(result, approx) < 3.0


def test_lunar_return_sequence_is_monotonic() -> None:
    natal = datetime(1995, 7, 14, 6, 0, tzinfo=UTC)
    returns = lunar_return_datetimes(natal, n=3, tz="UTC")

    assert len(returns) == 3
    assert returns[0] > natal
    assert all(later > earlier for earlier, later in zip(returns, returns[1:], strict=False))
    assert 25.0 < _days_between(returns[0], natal) < 30.0


def test_aries_ingress_occurs_in_march() -> None:
    ingress = aries_ingress_year(2024, tz="UTC")
    assert ingress.year == 2024
    assert ingress.month == 3
    assert 18 <= ingress.day <= 22
