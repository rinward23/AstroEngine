"""Acceptance tests for longitudinal aspect detection."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

from astroengine.detectors_aspects import AspectHit, _load_policy, detect_aspects


@dataclass
class SyntheticProvider:
    """Synthetic ephemeris provider returning predetermined positions."""

    default_state: dict[str, dict[str, float]]
    timeline: dict[str, dict[str, dict[str, float]]] | None = None

    def positions_ecliptic(
        self, iso: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:
        state = (self.timeline or {}).get(iso, self.default_state)
        return {body: dict(state[body]) for body in bodies}


def _write_policy(
    tmp_path: Path, *, minors: Iterable[str], harmonics: Iterable[int | str]
) -> Path:
    base_policy = json.loads(json.dumps(_load_policy()))
    base_policy["enabled_minors"] = [name for name in minors]
    base_policy["enabled_harmonics"] = [value for value in harmonics]
    out_path = tmp_path / "aspects_policy.json"
    out_path.write_text(json.dumps(base_policy), encoding="utf-8")
    return out_path


ASPECT_CASES = (
    ("conjunction", 0.0, "major"),
    ("sextile", 60.0, "major"),
    ("square", 90.0, "major"),
    ("trine", 120.0, "major"),
    ("opposition", 180.0, "major"),
    ("semisextile", 30.0, "minor"),
    ("semisquare", 45.0, "minor"),
    ("sesquisquare", 135.0, "minor"),
    ("quincunx", 150.0, "minor"),
    ("semiquintile", 36.0, "minor"),
    ("quintile", 72.0, "minor"),
    ("biquintile", 144.0, "minor"),
    ("novile", 40.0, "harmonic"),
    ("binovile", 80.0, "harmonic"),
    ("septile", 51.4286, "harmonic"),
    ("biseptile", 102.8571, "harmonic"),
    ("triseptile", 154.2857, "harmonic"),
    ("tredecile", 108.0, "harmonic"),
    ("undecile", 32.7273, "harmonic"),
)


@pytest.mark.parametrize("aspect_name, angle_deg, family", ASPECT_CASES)
@pytest.mark.parametrize("offset", (-0.05, 0.05))
def test_detect_aspects_hits_angles(
    tmp_path: Path, aspect_name: str, angle_deg: float, family: str, offset: float
) -> None:
    provider = SyntheticProvider(
        default_state={
            "moving": {"lon": 0.0, "speed_lon": 1.0},
            "target": {"lon": angle_deg + offset, "speed_lon": 0.0},
        }
    )
    policy_path = _write_policy(
        tmp_path,
        minors=(
            "semisextile",
            "semisquare",
            "sesquisquare",
            "quincunx",
            "semiquintile",
            "quintile",
            "biquintile",
        ),
        harmonics=(5, 7, 9, 10, 11),
    )
    hits = detect_aspects(
        provider,
        ["2024-01-01T00:00:00Z"],
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    kind = f"aspect_{aspect_name}"
    match: AspectHit | None = next((hit for hit in hits if hit.kind == kind), None)
    assert match is not None, f"missing {kind} hit"
    assert match.family == family
    assert match.orb_allow + 1e-6 >= abs(offset)
    assert match.orb_abs == pytest.approx(abs(offset), abs=1e-6)
    assert match.offset_deg == pytest.approx(offset, abs=1e-6)
    expected_delta = (angle_deg + offset) % 360.0
    assert match.delta_lambda_deg == pytest.approx(expected_delta, abs=1e-6)
    expected_phase = "applying" if offset < 0 else "separating"
    assert match.applying_or_separating == expected_phase
    assert match.is_partile is True


def test_partile_threshold_flags(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path, minors=("semisextile",), harmonics=())
    provider_partile = SyntheticProvider(
        default_state={
            "moving": {"lon": 0.0, "speed_lon": 0.8},
            "target": {"lon": 60.1, "speed_lon": 0.0},
        }
    )
    hits_partile = detect_aspects(
        provider_partile,
        ["2024-01-01T00:00:00Z"],
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    sextile = next(hit for hit in hits_partile if hit.kind == "aspect_sextile")
    assert sextile.is_partile is True

    provider_wide = SyntheticProvider(
        default_state={
            "moving": {"lon": 0.0, "speed_lon": 0.8},
            "target": {"lon": 60.4, "speed_lon": 0.0},
        }
    )
    hits_wide = detect_aspects(
        provider_wide,
        ["2024-01-02T00:00:00Z"],
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    sextile_wide = next(hit for hit in hits_wide if hit.kind == "aspect_sextile")
    assert sextile_wide.is_partile is False


def test_retrograde_and_relative_speed_classification(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path, minors=(), harmonics=())

    retro_provider = SyntheticProvider(
        default_state={
            "moving": {"lon": 0.0, "speed_lon": -0.5},
            "target": {"lon": 120.2, "speed_lon": 0.0},
        }
    )
    retro_hits = detect_aspects(
        retro_provider,
        ["2024-01-01T00:00:00Z"],
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    retro_trine = next(hit for hit in retro_hits if hit.kind == "aspect_trine")
    assert retro_trine.applying_or_separating == "applying"

    swap_provider = SyntheticProvider(
        default_state={
            "moving": {"lon": 0.0, "speed_lon": 0.2},
            "target": {"lon": 90.2, "speed_lon": 0.6},
        }
    )
    swap_hits = detect_aspects(
        swap_provider,
        ["2024-01-01T00:00:00Z"],
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    square_hit = next(hit for hit in swap_hits if hit.kind == "aspect_square")
    assert square_hit.applying_or_separating == "applying"


def test_delta_lambda_wraparound_continuity(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path,
        minors=("semisextile",),
        harmonics=(),
    )
    timeline = {
        "2024-01-01T00:00:00Z": {
            "moving": {"lon": 359.5, "speed_lon": 0.4},
            "target": {"lon": 29.6, "speed_lon": 0.0},
        },
        "2024-01-01T01:00:00Z": {
            "moving": {"lon": 0.6, "speed_lon": 0.4},
            "target": {"lon": 30.7, "speed_lon": 0.0},
        },
    }
    provider = SyntheticProvider(
        default_state=timeline["2024-01-01T00:00:00Z"], timeline=timeline
    )
    hits = detect_aspects(
        provider,
        list(timeline.keys()),
        "moving",
        "target",
        policy_path=str(policy_path),
    )
    semisextile_hits = [hit for hit in hits if hit.kind == "aspect_semisextile"]
    assert len(semisextile_hits) == 2
    for hit in semisextile_hits:
        assert hit.delta_lambda_deg == pytest.approx(30.1, abs=1e-6)
        assert abs(hit.offset_deg - 0.1) < 1e-6
