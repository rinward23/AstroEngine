from __future__ import annotations

from astroengine.engine.returns.attach import attach_transiting_aspects
from astroengine.scoring.policy import load_orb_policy


def test_transiting_aspects_harmonic_filter() -> None:
    policy = load_orb_policy()
    positions = {
        "timestamp": "2024-01-01T00:00:00Z",
        "bodies": {
            "Sun": {"lon": 0.0, "speed_lon": 0.9856},
            "Saturn": {"lon": 180.1, "speed_lon": 0.033},
            "Mars": {"lon": 90.0, "speed_lon": 0.6},
        },
    }

    hits = attach_transiting_aspects(positions, policy, (1, 2, 4))
    kinds = {hit.kind for hit in hits}
    assert "aspect_opposition" in kinds
    assert "aspect_square" in kinds

    conj_only = attach_transiting_aspects(positions, policy, (1,))
    assert conj_only == []
