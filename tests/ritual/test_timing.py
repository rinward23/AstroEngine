"""Tests for the ritual timing reference tables."""

from __future__ import annotations

from astroengine.ritual import (
    CHALDEAN_ORDER,
    ELECTIONAL_WINDOWS,
    PLANETARY_DAYS,
    PLANETARY_HOUR_TABLE,
    VOID_OF_COURSE_RULES,
)


def test_planetary_days_and_hours():
    assert len(PLANETARY_DAYS) == 7
    sunday = next(day for day in PLANETARY_DAYS if day.weekday == "Sunday")
    assert sunday.ruler == "Sun"
    hours = PLANETARY_HOUR_TABLE["Sunday"]
    assert len(hours) == 24
    assert hours[0] == "Sun"
    assert PLANETARY_HOUR_TABLE["Monday"][1] == "Saturn"
    assert CHALDEAN_ORDER == (
        "Saturn",
        "Jupiter",
        "Mars",
        "Sun",
        "Venus",
        "Mercury",
        "Moon",
    )


def test_filters_and_windows():
    assert len(VOID_OF_COURSE_RULES) >= 2
    rule_names = {rule.name for rule in VOID_OF_COURSE_RULES}
    assert "Classical void-of-course" in rule_names
    assert len(ELECTIONAL_WINDOWS) == 3
    waxing = next(
        window for window in ELECTIONAL_WINDOWS if window.name.startswith("Waxing")
    )
    assert "Moon increasing in light" in waxing.criteria
