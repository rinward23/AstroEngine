from __future__ import annotations

import json
from pathlib import Path

from astroengine.interpret.engine import evaluate
from astroengine.interpret.loader import load_rulepack


def load_hits() -> list[dict[str, float | int | str]]:
    hits_path = Path("tests/interpret/fixtures/hits_simple.json")
    return json.loads(hits_path.read_text(encoding="utf-8"))


def test_profile_weights_shift_scores() -> None:
    rulepack = load_rulepack("astroengine/interpret/examples/basic.yaml")
    hits = load_hits()

    balanced = evaluate(rulepack, scope="synastry", hits=hits, profile="balanced")
    chemistry = evaluate(rulepack, scope="synastry", hits=hits, profile="chemistry_plus")

    balanced_scores = {finding.id: finding.score for finding in balanced.findings}
    chemistry_scores = {finding.id: finding.score for finding in chemistry.findings}

    assert chemistry_scores["r.sun_moon_trine"] > balanced_scores["r.sun_moon_trine"]
    assert chemistry_scores["r.saturn_conj_venus"] <= balanced_scores["r.saturn_conj_venus"]
