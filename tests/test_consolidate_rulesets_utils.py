"""Tests for helper utilities in the ruleset consolidation workflow."""

from __future__ import annotations

import datetime as _dt
import runpy
from pathlib import Path

_MODULE_GLOBALS = runpy.run_path(
    Path(__file__).resolve().parents[1]
    / "Version Consolidation"
    / "consolidate_rulesets.py"
)
iso_to_dt = _MODULE_GLOBALS["iso_to_dt"]


def test_iso_to_dt_parses_iso_strings() -> None:
    result = iso_to_dt("2025-09-03T22:41Z")
    assert result == _dt.datetime(2025, 9, 3, 22, 41)


def test_iso_to_dt_strips_whitespace() -> None:
    result = iso_to_dt(" 2025-09-03 ")
    assert result == _dt.datetime(2025, 9, 3)


def test_iso_to_dt_accepts_datetime_instances() -> None:
    stamp = _dt.datetime(2024, 1, 2, 3, 4, 5)
    result = iso_to_dt(stamp)
    assert result is stamp


def test_iso_to_dt_handles_byte_like_inputs() -> None:
    result = iso_to_dt(b"2025-09-03T22:41")
    assert result == _dt.datetime(2025, 9, 3, 22, 41)

    result = iso_to_dt(memoryview(b"2025-09-03"))
    assert result == _dt.datetime(2025, 9, 3)


def test_iso_to_dt_returns_none_for_non_string_inputs() -> None:
    assert iso_to_dt(20250903) is None

    class Explosive:
        def __str__(self) -> str:  # pragma: no cover - exercised via iso_to_dt
            raise ValueError("boom")

    assert iso_to_dt(Explosive()) is None


def test_iso_to_dt_returns_none_for_empty_text() -> None:
    assert iso_to_dt("") is None
    assert iso_to_dt("   ") is None
