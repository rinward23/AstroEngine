from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from astroengine.config import Settings
from astroengine.geo.atlas import AtlasLookupError, GeocodeResult, geocode


def _offline_settings(db_path: Path) -> Settings:
    settings = Settings()
    settings.atlas.offline_enabled = True
    settings.atlas.data_path = str(db_path)
    return settings


def _materialize_offline_sample(tmp_path: Path) -> Path:
    sql_path = Path(__file__).resolve().parents[1] / "data" / "atlas" / "offline_sample.sql"
    db_path = tmp_path / "offline_sample.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(sql_path.read_text(encoding="utf-8"))
    return db_path


def test_geocode_offline_sample_city(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = _materialize_offline_sample(tmp_path)
    settings = _offline_settings(db_path)
    monkeypatch.setattr("astroengine.geo.atlas.load_settings", lambda: settings)

    result = geocode("London")
    assert result["name"] == "London, United Kingdom"
    assert result["tz"] == "Europe/London"
    assert result["lat"] == pytest.approx(51.5074, abs=1e-4)
    assert result["lon"] == pytest.approx(-0.1278, abs=1e-4)


def test_geocode_offline_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "missing.sqlite"
    settings = _offline_settings(db_path)
    monkeypatch.setattr("astroengine.geo.atlas.load_settings", lambda: settings)

    with pytest.raises(AtlasLookupError) as excinfo:
        geocode("Nowhere")
    assert "Offline atlas database not found" in str(excinfo.value)


def test_geocode_online_disabled_by_default() -> None:
    settings = Settings()

    with pytest.raises(AtlasLookupError) as excinfo:
        geocode("Anywhere", settings=settings)

    assert "Online atlas fallback is disabled" in str(excinfo.value)


def test_geocode_uses_online_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    settings.atlas.online_fallback_enabled = True

    calls: dict[str, int] = {"count": 0}

    def _fake_online(query: str) -> GeocodeResult:  # type: ignore[name-defined]
        calls["count"] += 1
        return {"name": query.title(), "lat": 1.0, "lon": 2.0, "tz": "UTC"}

    monkeypatch.setattr("astroengine.geo.atlas._geocode_online", _fake_online)

    result = geocode("sample", settings=settings)

    assert result["name"] == "Sample"
    assert calls["count"] == 1
