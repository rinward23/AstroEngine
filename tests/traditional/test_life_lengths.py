from __future__ import annotations

from dataclasses import dataclass

import pytest

from astroengine.engine.traditional.life_lengths import (
    _candidate_names,
    _score_dignities,
    _score_house,
    find_alcocoden,
    find_hyleg,
)
from astroengine.engine.traditional.models import HylegResult, LifeProfile


@dataclass
class DummySpan:
    ruler: str


class DummyDignities:
    def __init__(
        self,
        *,
        exaltation: str | None = None,
        triplicity_day: str | None = None,
        triplicity_night: str | None = None,
        bounds_ruler: str | None = None,
        face_ruler: str | None = None,
        bounds: tuple[DummySpan, ...] = (),
        decans: tuple[DummySpan, ...] = (),
    ) -> None:
        self.exaltation = exaltation
        self.triplicity_day = triplicity_day
        self.triplicity_night = triplicity_night
        self.triplicity_participating = None
        self._bounds_ruler = bounds_ruler
        self._face_ruler = face_ruler
        self.bounds = bounds
        self.decans = decans

    def bounds_ruler(self, degree: float) -> str | None:  # pragma: no cover - trivial
        return self._bounds_ruler

    def face_ruler(self, degree: float) -> str | None:  # pragma: no cover - trivial
        return self._face_ruler

    def triplicity_for_sect(self, sect: str) -> str | None:
        if sect.lower() == "day":
            return self.triplicity_day or self.triplicity_participating
        if sect.lower() == "night":
            return self.triplicity_night or self.triplicity_participating
        return self.triplicity_participating


@dataclass
class DummyPosition:
    longitude: float


@dataclass
class DummyHouses:
    ascendant: float | None


@dataclass
class DummyNatal:
    houses: DummyHouses
    positions: dict[str, DummyPosition]


@dataclass
class DummySect:
    is_day: bool
    luminary_of_sect: str


@dataclass
class DummyChartCtx:
    natal: DummyNatal
    sect: DummySect
    lots: dict[str, float]
    house_system: str = "whole_sign"

    def lot(self, name: str, default: float | None = None) -> float | None:
        return self.lots.get(name, default)


def test_score_house_respects_weight_classes() -> None:
    weights = {"angular": 1.1, "succedent": 0.7, "cadent": 0.3}
    assert _score_house(1, weights) == (1.1, "angular")
    assert _score_house(5, weights) == (0.7, "succedent")
    assert _score_house(9, weights) == (0.3, "cadent")
    assert _score_house(6, {}) == (0.25, "cadent")
    assert _score_house(13, weights) == (0.0, None)


def test_score_dignities_combines_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = LifeProfile()

    bundle = DummyDignities(
        exaltation="sun",
        triplicity_day="sun",
        bounds_ruler="sun",
        face_ruler="sun",
    )
    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.sign_dignities",
        lambda sign: bundle,
    )

    score, trace = _score_dignities("Sun", "leo", 15.0, profile, True)
    assert score == pytest.approx(
        profile.dignity_weights["rulership"]
        + profile.dignity_weights["exaltation"]
        + profile.dignity_weights["triplicity"]
        + profile.dignity_weights["bounds"]
        + profile.dignity_weights["face"]
    )
    tags = {name for name, _ in trace}
    assert {"rulership", "exaltation", "triplicity", "bounds", "face"}.issubset(tags)


def test_candidate_names_reflects_sect_and_lots() -> None:
    assert list(_candidate_names(True, False)) == ["Sun", "Moon", "Asc"]
    assert list(_candidate_names(False, False)) == ["Moon", "Sun", "Asc"]
    assert list(_candidate_names(True, True)) == ["Sun", "Moon", "Asc", "Fortune"]


def test_find_hyleg_raises_when_no_candidates() -> None:
    ctx = DummyChartCtx(
        natal=DummyNatal(
            houses=DummyHouses(ascendant=None),
            positions={},
        ),
        sect=DummySect(is_day=True, luminary_of_sect="Sun"),
        lots={},
    )
    profile = LifeProfile(include_fortune=False)

    with pytest.raises(ValueError, match="No suitable Hyleg"):
        find_hyleg(ctx, profile)


def test_find_alcocoden_uses_dignity_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = DummyChartCtx(
        natal=DummyNatal(houses=DummyHouses(ascendant=0.0), positions={}),
        sect=DummySect(is_day=True, luminary_of_sect="Sun"),
        lots={},
    )
    profile = LifeProfile()
    hyleg = HylegResult(
        body="Sun",
        degree=120.0,
        sign="leo",
        house=1,
        score=0.0,
        notes=(),
        trace=(),
    )

    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.bounds_ruler",
        lambda sign, degree: None,
    )

    bundle = DummyDignities(
        exaltation="saturn",
        triplicity_day="jupiter",
        bounds=tuple(DummySpan(ruler="sun") for _ in range(2)),
        decans=tuple(DummySpan(ruler="sun") for _ in range(1)),
    )

    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.sign_dignities",
        lambda sign: bundle,
    )

    result = find_alcocoden(ctx, hyleg, profile)
    assert result.body == "Sun"
    assert result.method == "dignities"
    assert result.confidence == pytest.approx(0.55)
    assert "method=dignities" in result.notes
    assert any(trace.startswith("rulership") for trace in result.trace)


def test_find_alcocoden_raises_when_no_dignity_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = DummyChartCtx(
        natal=DummyNatal(houses=DummyHouses(ascendant=0.0), positions={}),
        sect=DummySect(is_day=False, luminary_of_sect="Moon"),
        lots={},
    )
    profile = LifeProfile()
    hyleg = HylegResult(
        body="Moon",
        degree=45.0,
        sign="void",
        house=1,
        score=0.0,
        notes=(),
        trace=(),
    )

    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.bounds_ruler",
        lambda sign, degree: None,
    )
    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.SIGN_RULERS",
        {"aries": "mars"},
    )

    empty_bundle = DummyDignities()
    monkeypatch.setattr(
        "astroengine.engine.traditional.life_lengths.sign_dignities",
        lambda sign: empty_bundle,
    )

    with pytest.raises(ValueError, match="Unable to determine Alcocoden"):
        find_alcocoden(ctx, hyleg, profile)
