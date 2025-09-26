"""Lightweight job handler registry used by the background scheduler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..core.transit_engine import scan_transits as _scan_transits
from ..detectors.directions import solar_arc_directions as _scan_directions
from ..detectors.progressions import secondary_progressions as _scan_progressions
from ..detectors.returns import scan_returns as _scan_returns

Handler = Callable[[dict[str, Any]], object]


def _invoke(fn: Callable[..., object], params: dict[str, Any]) -> object:
    return fn(**params)


HANDLERS: dict[str, Handler] = {
    "scan:progressions": lambda payload: _invoke(_scan_progressions, payload),
    "scan:directions": lambda payload: _invoke(_scan_directions, payload),
    "scan:transits": lambda payload: _invoke(_scan_transits, payload),
    "scan:returns": lambda payload: _invoke(_scan_returns, payload),
}
