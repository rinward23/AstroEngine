from __future__ import annotations

from astroengine.data.schemas import list_schema_keys, load_schema_document
from astroengine.validation import available_schema_keys


def test_orbs_policy_contains_expected_entries():
    data = load_schema_document("orbs_policy")
    assert data["schema"]["id"] == "astroengine.orbs.policy"
    assert data["profiles"]["standard"]["multipliers"]["luminaries"] == 1.2
    assert data["aspects"]["conjunction"]["base_orb"] == 8.0
    assert set(data["aspects"].keys()) == {
        "conjunction",
        "opposition",
        "square",
        "trine",
        "sextile",
        "quincunx",
    }


def test_available_schema_keys_filters_jsonschemas():
    json_schemas = available_schema_keys("jsonschema")
    assert "result_v1" in json_schemas
    assert "contact_gate_v2" in json_schemas
    assert "orbs_policy" not in json_schemas

    all_keys = set(list_schema_keys())
    assert {"result_v1", "contact_gate_v2", "orbs_policy"}.issubset(all_keys)
