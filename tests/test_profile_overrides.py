from __future__ import annotations

import yaml

from astroengine.profiles import load_profile


def test_load_profile_includes_policies() -> None:
    profile = load_profile()
    policies = profile["policies"]
    assert "orb" in policies
    assert "severity" in policies
    assert "visibility" in policies
    assert policies["severity"]["condition_modifiers"]["retrograde"] == 0.92


def test_user_override_merges(tmp_path) -> None:
    overrides_path = tmp_path / "user_overrides.yaml"
    overrides_path.write_text(
        yaml.safe_dump(
            {
                "users": {
                    "tester": {
                        "policies": {
                            "severity": {"base_weights": {"aspect_conjunction": 0.5}}
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    profile = load_profile(user="tester", overrides_path=overrides_path)
    assert profile["policies"]["severity"]["base_weights"]["aspect_conjunction"] == 0.5


def test_runtime_override_has_highest_precedence() -> None:
    profile = load_profile(
        overrides={"policies": {"severity": {"base_weights": {"aspect_square": 1.5}}}}
    )
    assert profile["policies"]["severity"]["base_weights"]["aspect_square"] == 1.5
