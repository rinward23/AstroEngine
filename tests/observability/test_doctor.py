from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from astroengine.observability import doctor


class _DummySample:
    def __init__(self, longitude: float, declination: float) -> None:
        self.longitude = longitude
        self.declination = declination


class _DummyAdapter:
    def body_position(self, jd_ut: float, _code: int, body_name: str | None = None) -> _DummySample:
        return _DummySample(longitude=jd_ut % 360.0, declination=0.0)


class _DummySwissAdapter:
    @staticmethod
    def get_default_adapter() -> _DummyAdapter:
        return _DummyAdapter()


def _fake_check(name: str) -> doctor.DoctorCheck:
    return doctor.DoctorCheck(name=name, status="ok", detail="ok")


def test_run_system_doctor_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    swe_dir = tmp_path / "swisseph"
    swe_dir.mkdir()

    fake_swe = types.SimpleNamespace(
        __version__="2.10",
        SUN=0,
        julday=lambda year, *_args: float(year),
    )
    monkeypatch.setitem(sys.modules, "swisseph", fake_swe)
    monkeypatch.setattr(doctor, "_get_default_adapter", _DummySwissAdapter.get_default_adapter)
    monkeypatch.setattr(doctor, "get_se_ephe_path", lambda: str(swe_dir))
    monkeypatch.setattr(doctor, "_check_database", lambda: _fake_check("database"))
    monkeypatch.setattr(doctor, "_check_migrations", lambda: _fake_check("migrations"))
    monkeypatch.setattr(doctor, "_check_cache", lambda: _fake_check("cache"))

    settings = types.SimpleNamespace(
        swiss_caps=types.SimpleNamespace(min_year=1900, max_year=1901)
    )

    report = doctor.run_system_doctor(settings=settings)

    assert report["status"] == "ok"
    swiss = report["checks"]["swiss_ephemeris"]
    samples = swiss["data"]["range_samples"]
    years = {entry["year"] for entry in samples}
    assert years == {1900, 1901}


def test_run_system_doctor_missing_swisseph(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_import(name: str) -> None:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(doctor, "import_module", _raise_import)
    monkeypatch.setattr(doctor, "_check_database", lambda: _fake_check("database"))
    monkeypatch.setattr(doctor, "_check_migrations", lambda: _fake_check("migrations"))
    monkeypatch.setattr(doctor, "_check_cache", lambda: _fake_check("cache"))

    settings = types.SimpleNamespace(
        swiss_caps=types.SimpleNamespace(min_year=1900, max_year=1901)
    )

    report = doctor.run_system_doctor(settings=settings)
    assert report["status"] == "error"
    assert report["checks"]["swiss_ephemeris"]["status"] == "error"
