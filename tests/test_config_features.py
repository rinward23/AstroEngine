from __future__ import annotations

import pytest

from astroengine.config.features import (
    EXPERIMENTAL_MODALITIES,
    IMPLEMENTED_MODALITIES,
    available_modalities,
    experimental_modalities_from_env,
    is_enabled,
)


def test_available_modalities_matches_implemented():
    assert available_modalities() == tuple(sorted(IMPLEMENTED_MODALITIES))


def test_is_enabled_handles_experimental_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert is_enabled("lunations")
    assert not is_enabled("prog-aspects")

    monkeypatch.setenv("ASTROENGINE_EXPERIMENTAL_MODALITIES", "prog-aspects")
    experimental_modalities_from_env.cache_clear()
    try:
        assert is_enabled("prog-aspects")
    finally:
        monkeypatch.delenv("ASTROENGINE_EXPERIMENTAL_MODALITIES", raising=False)
        experimental_modalities_from_env.cache_clear()


@pytest.mark.parametrize("name", sorted(EXPERIMENTAL_MODALITIES))
def test_is_enabled_programmatic_opt_in(name: str) -> None:
    assert is_enabled(name, experimental=True)


@pytest.mark.parametrize("name", ["", "unknown", None])
def test_is_enabled_unknown(name: str | None) -> None:
    assert not is_enabled(name or "")
