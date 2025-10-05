from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip(
    "jinja2",
    reason="jinja2 not installed; install extras with `pip install -e .[narrative,reports]`.",
)

from astroengine.interpret.engine import evaluate
from astroengine.interpret.loader import load_rulepack
from astroengine.interpret.templates import get_renderer


def load_hits() -> list[dict[str, float | int | str]]:
    hits_path = Path("tests/interpret/fixtures/hits_simple.json")
    return json.loads(hits_path.read_text(encoding="utf-8"))


def test_engine_matches_and_scores() -> None:
    rulepack = load_rulepack("astroengine/interpret/examples/basic.yaml")
    hits = load_hits()

    result = evaluate(rulepack, scope="synastry", hits=hits, profile="balanced")
    assert result.findings, "Expected at least one finding"

    sun_moon = next(f for f in result.findings if f.id == "r.sun_moon_trine")
    assert sun_moon.score > 0.5
    assert "chemistry" in sun_moon.tags

    totals = result.totals
    assert totals["overall"] >= sun_moon.score
    assert totals["by_tag"]["chemistry"] >= sun_moon.score


def test_engine_template_rendering() -> None:
    rulepack = load_rulepack("astroengine/interpret/examples/basic.yaml")
    hits = load_hits()[:1]
    renderer = get_renderer()

    result = evaluate(rulepack, scope="synastry", hits=hits, renderer=renderer)
    assert result.findings[0].markdown is not None
    assert "Sun (A)" in result.findings[0].markdown
