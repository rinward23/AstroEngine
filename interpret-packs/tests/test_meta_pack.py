from __future__ import annotations

from pathlib import Path

from core.interpret_plus.engine import load_rules

BASE = Path(__file__).resolve().parents[1]


def test_meta_pack_combines_rules():
    pack = load_rules(str(BASE / "meta" / "essentials.yaml"))
    assert pack["rulepack"] == "relationship-essentials"
    assert len(pack["rules"]) > 60
    assert "saturn-binding-growth" in pack["meta"].get("includes", [])
    assert "chemistry_plus" in pack["profiles"]
