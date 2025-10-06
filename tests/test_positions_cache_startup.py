from __future__ import annotations

from astroengine.cache import positions_cache


def test_warm_startup_grid_respects_time_budget(monkeypatch):
    calls: list[tuple[float, str]] = []
    current = {"value": 0.0}

    def fake_perf_counter() -> float:
        return current["value"]

    def fake_get_daily_entry(jd: float, body: str) -> tuple[float, float, float]:
        calls.append((jd, body))
        current["value"] += 0.2  # simulate 200 ms of work per call
        return 0.0, 0.0, 0.0

    monkeypatch.setattr(positions_cache, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(positions_cache, "get_daily_entry", fake_get_daily_entry)

    warmed = positions_cache.warm_startup_grid(
        max_duration_ms=150.0,
        bodies=("sun", "moon"),
        day_offsets=(0, 1),
    )

    assert warmed == 1
    assert len(calls) == 1


def test_warm_startup_grid_ignores_unsupported(monkeypatch):
    monkeypatch.setattr(
        positions_cache,
        "get_daily_entry",
        lambda *_args, **_kwargs: (_args[0], _args[1], 0.0),
    )

    warmed = positions_cache.warm_startup_grid(
        max_duration_ms=150.0,
        bodies=("unknown",),
        day_offsets=(0,),
    )

    assert warmed == 0


def test_warm_startup_grid_handles_runtime_error(monkeypatch):
    def raise_runtime_error(_jd: float, _body: str) -> tuple[float, float, float]:
        raise RuntimeError("Swiss unavailable")

    monkeypatch.setattr(positions_cache, "get_daily_entry", raise_runtime_error)
    monkeypatch.setattr(positions_cache, "perf_counter", lambda: 0.0)

    warmed = positions_cache.warm_startup_grid(
        max_duration_ms=150.0,
        bodies=("sun",),
        day_offsets=(0,),
    )

    assert warmed == 0
