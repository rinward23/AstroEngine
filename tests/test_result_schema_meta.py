# >>> AUTO-GEN BEGIN: Test Result Schema Meta v1.0
import json
import os
import pytest

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


def test_result_schema_is_valid_jsonschema():
    schema_path = os.path.join("schemas", "result_schema_v1.json")
    if not os.path.exists(schema_path):
        pytest.skip("schemas/result_schema_v1.json not found")
    if jsonschema is None:
        pytest.skip("jsonschema not installed")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    metas = [
        getattr(jsonschema, "Draft202012Validator", None),
        getattr(jsonschema, "Draft201909Validator", None),
        getattr(jsonschema, "Draft7Validator", None),
    ]
    metas = [m for m in metas if m is not None]
    assert metas, "No suitable jsonschema meta-validator available"

    metas[0].check_schema(schema)


# >>> AUTO-GEN END: Test Result Schema Meta v1.0
