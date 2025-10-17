from __future__ import annotations

from typing import Any, Mapping

import pytest

from astroengine.scoring import contact
from astroengine.scoring.contact import ScoreInputs, compute_score, compute_uncertainty_confidence


class DummyTradition:
    def __init__(self, angles: Mapping[str, tuple[float, ...]] | None = None) -> None:
        self._angles = {key: tuple(value) for key, value in (angles or {}).items()}

    def drishti_angles(self, body: str) -> tuple[float, ...]:
        return self._angles.get(body, (60.0,))

    def drishti_scalar(self, body: str) -> float:
        return 0.25

    def resonance_bias(self) -> Mapping[str, float]:
        return {"mind": 0.9}


def test_modifier_factors_collect_expected_components() -> None:
    policy = {
        "dignity_weights": {"domicile": 1.5, "exaltation": 1.2},
        "condition_modifiers": {"retrograde": 0.8, "combust": 0.7, "out_of_bounds": 1.3},
        "sect_bias": {"day": {"luminaries": {"Sun": 1.1, "Moon": 0.9}}},
    }
    inputs = ScoreInputs(
        kind="conjunction",
        orb_abs_deg=0.5,
        orb_allow_deg=5.0,
        moving="Sun",
        target="Moon",
        applying_or_separating="applying",
        dignity_modifiers={"Sun": "domicile", "numeric": 1.1, "Moon": "unknown"},
        retrograde=True,
        combust_state="combust",
        out_of_bounds=True,
        custom_modifiers={"custom": 1.05},
        chart_sect="day",
    )

    dignity_factor, dignity_components = contact._dignity_factor(policy, inputs)
    condition_factor, condition_components = contact._condition_factor(policy, inputs)

    assert dignity_factor == pytest.approx(1.65)
    assert dignity_components == {"Sun:domicile": 1.5, "numeric": 1.1}

    expected_condition = 0.8 * 0.7 * 1.3 * 1.05 * 1.1 * 0.9
    assert condition_factor == pytest.approx(expected_condition)
    assert condition_components["retrograde"] == 0.8
    assert condition_components["combust"] == 0.7
    assert condition_components["out_of_bounds"] == 1.3
    assert condition_components["custom"] == 1.05
    assert condition_components["sect:Sun:luminaries"] == 1.1
    assert condition_components["sect:Moon:luminaries"] == 0.9


def test_compute_score_aggregates_components(monkeypatch: pytest.MonkeyPatch) -> None:
    policy_payload: dict[str, Any] = {
        "base_weights": {"conjunction": 0.6},
        "curve": {"sigma_frac_of_orb": 0.5, "min_score": 0.1, "max_score": 1.0},
        "body_class_weights": {"luminary": 1.1},
        "pair_matrix": {"luminary-luminary": 1.05},
        "condition_modifiers": {"retrograde": 0.9, "combust": 0.8},
        "dignity_weights": {"ruler": 1.2},
        "traditions": {
            "hellenistic": {
                "curve": {"max_score": 1.2},
                "condition_modifiers": {"combust": 0.85},
                "dignity_weights": {"ruler": 1.3},
                "fractal_patterns": {"enabled": False},
            }
        },
        "applying_bias": {"enabled": True, "factor": 1.1},
        "partile": {"enabled": True, "threshold_deg": 0.5, "boost_factor": 1.05},
        "sect_bias": {"day": {"luminaries": {"Sun": 1.05, "Moon": 0.95}}},
        "fractal_patterns": {
            "enabled": True,
            "harmonics": (2, 3),
            "baseline": 0.4,
            "spread": 0.5,
            "softness": 0.7,
        },
        "body_severity_weights": {"Sun": 1.2},
    }

    load_calls: list[str] = []

    def fake_load_json(path: Any) -> dict[str, Any]:
        load_calls.append(str(path))
        return policy_payload

    def fake_apply_extensions(inputs: ScoreInputs, result: contact.ScoreResult) -> contact.ScoreResult:
        return result

    dummy_tradition = DummyTradition()

    monkeypatch.setattr(contact, "load_json_document", fake_load_json)
    monkeypatch.setattr(contact, "apply_score_extensions", fake_apply_extensions)
    monkeypatch.setattr(contact, "get_tradition_spec", lambda name: dummy_tradition)
    contact._load_policy.cache_clear()

    inputs = ScoreInputs(
        kind="conjunction",
        orb_abs_deg=1.0,
        orb_allow_deg=5.0,
        moving="Sun",
        target="Moon",
        applying_or_separating="applying",
        corridor_width_deg=4.0,
        resonance_weights={"mind": 1.0, "body": 1.0, "spirit": 1.0},
        dignity_modifiers={"status": "ruler"},
        retrograde=True,
        combust_state="combust",
        custom_modifiers={"custom": 1.05},
        angle_deg=60.0,
        tradition_profile="hellenistic",
        chart_sect="day",
        observers=2,
        uncertainty_bias={"standard": "mind", "narrow": "spirit", "broad": "body"},
    )

    result_one = compute_score(inputs, policy_path="profiles/scoring_policy.json")
    result_two = compute_score(inputs, policy_path="profiles/scoring_policy.json")

    assert len(load_calls) == 1
    assert result_one.score == pytest.approx(0.12189740125734201)
    assert result_one.confidence == pytest.approx(0.13343549133033789)
    assert result_one.components["gaussian"] == pytest.approx(0.9231163463866358)
    assert result_one.components["corridor_factor"] == pytest.approx(0.8824969025845955)
    assert result_one.components["confidence"] == pytest.approx(result_one.confidence)
    assert result_one.components["tradition_factor"] == pytest.approx(1.05)
    assert result_one.components["dignity_factor"] == pytest.approx(1.3)
    assert result_one.components["condition_factor"] == pytest.approx(0.801241875)
    assert result_one.components["resonance_components"]["focus"] == "spirit"
    assert result_one.components["tradition_override"] == [
        "curve",
        "condition_modifiers",
        "dignity_weights",
        "fractal_patterns",
    ]

    expected_confidence = compute_uncertainty_confidence(
        inputs.orb_allow_deg,
        inputs.corridor_width_deg,
        observers=inputs.observers,
        overlap_count=inputs.overlap_count,
        orb_abs_deg=inputs.orb_abs_deg,
        resonance_weights=inputs.resonance_weights,
        uncertainty_bias=inputs.uncertainty_bias,
    )
    assert expected_confidence == pytest.approx(result_one.confidence)

    # Ensure the cached policy does not mutate across calls.
    assert result_two.components["gaussian"] == result_one.components["gaussian"]
