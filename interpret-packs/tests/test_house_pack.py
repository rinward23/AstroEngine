from __future__ import annotations

import json
from pathlib import Path

from core.interpret_plus.engine import interpret, load_rules

BASE = Path(__file__).resolve().parents[1]
FIXTURES = BASE / "fixtures"

with (FIXTURES / "composite_positions.json").open("r", encoding="utf-8") as handle:
    COMPOSITE = json.load(handle)
with (FIXTURES / "davison_positions.json").open("r", encoding="utf-8") as handle:
    DAVISON = json.load(handle)
with (FIXTURES / "golden_outputs.json").open("r", encoding="utf-8") as handle:
    GOLDEN = json.load(handle)


def _top(findings):
    return [
        {
            "id": f.id,
            "score": round(f.score, 4),
            "tags": f.tags[:],
        }
        for f in findings[:5]
    ]


def test_house_overlay_composite_golden():
    pack = load_rules(str(BASE / "packs" / "house-overlays.yaml"))
    req = {"scope": "composite", **COMPOSITE}
    findings = interpret(req, pack)
    assert _top(findings) == GOLDEN["house_composite"]


def test_house_overlay_davison_golden():
    pack = load_rules(str(BASE / "packs" / "house-overlays.yaml"))
    req = {"scope": "davison", **DAVISON}
    findings = interpret(req, pack)
    assert _top(findings) == GOLDEN["house_davison"]
