from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_swe_delta_t_profile_and_doc_remain_in_sync() -> None:
    """Ensure the Swiss Ephemeris delta-T toggle stays documented and profiled."""

    profile = yaml.safe_load(
        Path("profiles/base_profile.yaml").read_text(encoding="utf-8")
    )
    swe_config = profile["providers"]["swe"]

    assert "delta_t" in swe_config, "profiles/base_profile.yaml must expose providers.swe.delta_t"
    assert swe_config["delta_t"] is None, "Default should defer to swe.DELTAT_DEFAULT"

    providers_doc = Path("docs/module/providers_and_frames.md").read_text(
        encoding="utf-8"
    )
    assert "`providers.swe.delta_t`" in providers_doc

    feature_flags_doc = Path("profiles/feature_flags.md").read_text(encoding="utf-8")
    assert "`providers.swe.delta_t`" in feature_flags_doc
