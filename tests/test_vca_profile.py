import json

from astroengine.config import load_profile_json, profile_into_ctx
from astroengine.engine import get_active_aspect_angles


def test_profile_load_and_angles(tmp_path):
    path = tmp_path / "mini.json"
    path.write_text(
        json.dumps(
            {
                "id": "mini",
                "aspects": {"major": [0, 60, 90, 120, 180], "minor": [30]},
                "orbs": {"major": {"0": 8}},
                "flags": {"enable_antiscia": True},
            }
        ),
        encoding="utf-8",
    )
    profile = load_profile_json(path)
    ctx = profile_into_ctx({}, profile)
    angles = get_active_aspect_angles(ctx)
    assert 0.0 in angles
    assert 180.0 in angles
    assert 30.0 in angles
