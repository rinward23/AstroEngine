"""Unit tests for `astroengine.timelords.dashas` that avoid Swiss Ephemeris."""

from __future__ import annotations

import math
import sys
import types
from typing import Callable

import pytest


if "astroengine.modules.esoteric" not in sys.modules:
    stub_esoteric = types.ModuleType("astroengine.modules.esoteric")

    def _noop_register(_registry):  # pragma: no cover - defensive guard
        return None

    stub_esoteric.register_esoteric_module = _noop_register
    sys.modules["astroengine.modules.esoteric"] = stub_esoteric

from astroengine.timelords import dashas


def _install_fake_ephemeris(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, str, str, float, float, dict[str, float], Callable[[float], str]]:
    """Monkeypatch the Swiss Ephemeris hooks used by `vimsottari_dashas`.

    The replacements return deterministic values so the algorithm can be exercised
    without requiring the real Swiss Ephemeris binary data.
    """

    natal_ts = "fake-natal"
    start_ts = "fake-start"
    end_ts = "fake-end"

    natal_jd = 1000.0
    ketu_span = dashas._DASHA_YEARS["Ketu"] * dashas.SIDEREAL_YEAR_DAYS
    venus_span = dashas._DASHA_YEARS["Venus"] * dashas.SIDEREAL_YEAR_DAYS

    start_jd = natal_jd + ketu_span + 1.0
    end_jd = start_jd + venus_span / 2.0

    mapping = {
        natal_ts: natal_jd,
        start_ts: start_jd,
        end_ts: end_jd,
    }

    def fake_iso_to_jd(ts: str) -> float:
        try:
            return mapping[ts]
        except KeyError as exc:  # pragma: no cover - defensive clarity during debugging
            raise AssertionError(f"unexpected timestamp: {ts}") from exc

    def fake_jd_to_iso(jd: float) -> str:
        return f"patched-{jd:.6f}"

    def fake_moon_lon(_jd: float) -> float:
        return 0.0

    monkeypatch.setattr(dashas, "iso_to_jd", fake_iso_to_jd)
    monkeypatch.setattr(dashas, "jd_to_iso", fake_jd_to_iso)
    monkeypatch.setattr(dashas, "moon_lon", fake_moon_lon)

    return natal_ts, start_ts, end_ts, start_jd, end_jd, mapping, fake_jd_to_iso


def test_vimsottari_dashas_skips_prior_segments_without_partials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Earlier major periods ending before the window are omitted when partials are disabled."""

    (
        natal_ts,
        start_ts,
        end_ts,
        start_jd,
        end_jd,
        mapping,
        fake_jd_to_iso,
    ) = _install_fake_ephemeris(monkeypatch)

    periods = dashas.vimsottari_dashas(natal_ts, start_ts, end_ts, include_partial=False)

    assert periods, "expected later periods to be generated"

    ketu_span = dashas._DASHA_YEARS["Ketu"] * dashas.SIDEREAL_YEAR_DAYS
    ketu_end = mapping[natal_ts] + ketu_span
    assert ketu_end < start_jd

    first = periods[0]
    assert first.major_lord == "Venus"
    assert all(period.major_lord != "Ketu" for period in periods)
    assert first.ts.startswith("patched-")
    assert first.end_ts.startswith("patched-")
    assert first.jd >= mapping[natal_ts] + ketu_span
    assert first.jd < first.end_jd <= end_jd

    venus_span = dashas._DASHA_YEARS["Venus"] * dashas.SIDEREAL_YEAR_DAYS
    expected_fraction = dashas._DASHA_YEARS[first.sub_lord] / dashas._TOTAL_SEQUENCE_YEARS
    expected_length = venus_span * expected_fraction
    assert math.isclose(first.end_jd - first.jd, expected_length, rel_tol=1e-9)


def test_vimsottari_dashas_processes_prior_major_with_partials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allowing partials processes the major period that was previously skipped."""

    natal_ts, start_ts, end_ts, *_ = _install_fake_ephemeris(monkeypatch)

    original_sub_periods = dashas._sub_periods
    seen_major_indices: list[int] = []

    def tracking_sub_periods(
        major_index: int,
        major_start: float,
        major_end: float,
        start_fraction: float,
    ) -> list[tuple[int, str, float, float]]:
        seen_major_indices.append(major_index)
        return list(original_sub_periods(major_index, major_start, major_end, start_fraction))

    monkeypatch.setattr(dashas, "_sub_periods", tracking_sub_periods)

    dashas.vimsottari_dashas(natal_ts, start_ts, end_ts, include_partial=False)
    assert 0 not in seen_major_indices, "Ketu major should be skipped when partials are disabled"

    seen_major_indices.clear()
    periods = dashas.vimsottari_dashas(natal_ts, start_ts, end_ts, include_partial=True)
    assert 0 in seen_major_indices, "partials should evaluate the previously skipped Ketu major"
    assert periods, "expected at least one daśā period from later majors"

    first = periods[0]
    assert first.ts.startswith("patched-")
    assert first.end_ts.startswith("patched-")
