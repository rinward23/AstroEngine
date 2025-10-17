from __future__ import annotations

from astroengine import analysis
from astroengine.analysis import returns


def test_return_error_is_reexported() -> None:
    assert analysis.ReturnComputationError is returns.ReturnComputationError
