"""Property-style tests ensuring severity monotonicity."""

from __future__ import annotations

from astroengine.synastry.engine import ChartPositions, DEFAULT_ORB_POLICY, detect_hits


def test_severity_monotonic() -> None:
    base = ChartPositions({"Sun": 0.0})
    severities: list[float] = []
    for delta in [0.0, 1.0, 2.0, 3.0, 4.0]:
        target = ChartPositions({"Moon": 120.0 + delta})
        hits = detect_hits(base, target, aspects=(120,), policy=DEFAULT_ORB_POLICY)
        assert hits, "expected hit within orb"
        severities.append(hits[0].severity)
    assert severities == sorted(severities, reverse=True)

