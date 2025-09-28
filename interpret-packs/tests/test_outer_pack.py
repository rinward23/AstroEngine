from __future__ import annotations

import json
from pathlib import Path

from core.interpret_plus.engine import interpret, load_rules

BASE = Path(__file__).resolve().parents[1]
FIXTURES = BASE / "fixtures"

with (FIXTURES / "hits_canonical.json").open("r", encoding="utf-8") as handle:
    HITS = json.load(handle)
with (FIXTURES / "golden_outputs.json").open("r", encoding="utf-8") as handle:
    GOLDEN = json.load(handle)["outer"]


def _top(findings):
    return [
        {
            "id": f.id,
            "score": round(f.score, 4),
            "tags": f.tags[:],
            "source": f.meta.get("source_pack"),
        }
        for f in findings[:5]
    ]


def test_outer_planet_pack_matches_golden():
    pack = load_rules(str(BASE / "packs" / "outer-planet-contacts.yaml"))
    req = {"scope": "synastry", "profile": "chemistry_plus", "hits": HITS}
    findings = interpret(req, pack)
    assert _top(findings) == GOLDEN
