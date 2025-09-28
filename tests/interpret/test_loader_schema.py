from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from astroengine.interpret.loader import (
    RulepackValidationError,
    load_rulepack,
    load_rulepack_from_data,
)


def test_load_rulepack_roundtrip(tmp_path: Path) -> None:
    rulepack_path = Path("astroengine/interpret/examples/basic.yaml")
    loaded = load_rulepack(rulepack_path)
    assert loaded.rulepack == "relationship-basic"
    assert "balanced" in loaded.profiles
    assert loaded.rules[0].id == "r.sun_moon_trine"

    # Ensure JSON loading path works too.
    data = yaml.safe_load(rulepack_path.read_text(encoding="utf-8"))
    json_path = tmp_path / "basic.json"
    json_path.write_text(json.dumps(data), encoding="utf-8")
    json_loaded = load_rulepack(json_path)
    assert json_loaded.rulepack == loaded.rulepack


def test_load_rulepack_validation_error() -> None:
    with pytest.raises(RulepackValidationError):
        load_rulepack_from_data({"rulepack": "oops"})
