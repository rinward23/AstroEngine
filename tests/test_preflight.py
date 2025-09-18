# >>> AUTO-GEN BEGIN: Transit Preflight Tests v1.0
from __future__ import annotations

from pathlib import Path

from astroengine.dev.preflight import ruleset_has_module, upsert_autogen_block


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    old, new, changed = upsert_autogen_block(str(path), "X", "print('hi')\n")
    assert changed
    path.write_text(new, encoding="utf-8")
    old2, new2, changed2 = upsert_autogen_block(str(path), "X", "print('hi')\n")
    assert not changed2
    assert new2 == old2


def test_ruleset_has_module(tmp_path: Path) -> None:
    ruleset = tmp_path / "rules.yaml"
    ruleset.write_text("modules:\n  - id: transit.scan\n", encoding="utf-8")
    assert ruleset_has_module(str(ruleset), "transit.scan")
# >>> AUTO-GEN END: Transit Preflight Tests v1.0
