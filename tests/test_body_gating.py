"""Smoke tests for extended body classification and gating utilities."""

from __future__ import annotations

from datetime import timedelta

from astroengine.core.bodies import (
    ALL_SUPPORTED_BODIES,
    body_class,
    body_priority,
    canonical_name,
    step_multiplier,
)
from astroengine.scheduling.gating import choose_step, sort_bodies_for_scan


def test_extended_body_catalogue() -> None:
    required = {"sun", "moon", "mean_node", "mean_lilith", "vertex", "eris", "chiron"}
    assert required.issubset(ALL_SUPPORTED_BODIES)
    assert body_class("Mean_Node") == "point"
    assert canonical_name("Black_Moon_Lilith") == "mean_lilith"


def test_gating_step_priorities() -> None:
    fast = choose_step("day", "Sun")
    slow = choose_step("day", "Eris")
    assert isinstance(fast, timedelta) and isinstance(slow, timedelta)
    assert slow > fast
    assert step_multiplier("Sun") <= step_multiplier("Eris")
    assert body_priority("Moon") <= body_priority("Eris")


def test_sort_bodies_for_scan() -> None:
    ordered = sort_bodies_for_scan(["Pluto", "Moon", "Eris", "Mars", "Moon"])
    assert ordered[0] == "moon"
    assert ordered[-1] in {"eris", "pluto"}
