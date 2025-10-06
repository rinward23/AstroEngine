from __future__ import annotations

from astroengine.core.rel_plus import synastry as core_synastry
from core.rel_plus import synastry as plus_synastry


def test_memoization_prevents_duplicate_work(monkeypatch):
    plus_synastry.clear_synastry_memoization()
    calls = 0

    original = plus_synastry.match_pair

    def counting_match(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(plus_synastry, "match_pair", counting_match)

    pos_a = {"Sun": 10.0}
    pos_b = {"Sun": 10.2}
    aspects = ["conjunction", "sextile"]
    policy = {"per_aspect": {"conjunction": 8.0, "sextile": 4.0}}

    plus_synastry.synastry_interaspects(pos_a, pos_b, aspects, policy)
    first_calls = calls
    assert first_calls > 0

    calls = 0
    second = plus_synastry.synastry_interaspects(pos_a, pos_b, aspects, policy)
    assert calls == 0
    # returned list should be independent copy
    second[0]["orb"] = 99.0
    third = plus_synastry.synastry_interaspects(pos_a, pos_b, aspects, policy)
    assert third[0]["orb"] != 99.0

    monkeypatch.setattr(plus_synastry, "match_pair", original)


def test_core_synastry_memoization_isolated():
    core_synastry.clear_synastry_memoization()
    res1 = core_synastry.synastry_interaspects(
        {"Sun": 12.0},
        {"Sun": 192.0},
        ["opposition"],
        {"per_aspect": {"opposition": 6.0}},
    )
    res2 = core_synastry.synastry_interaspects(
        {"Sun": 12.0},
        {"Sun": 192.0},
        ["opposition"],
        {"per_aspect": {"opposition": 6.0}},
    )
    assert res1 == res2
