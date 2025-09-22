"""Smoke-tests for expanded esoteric correspondences."""

from __future__ import annotations

from astroengine.esoteric import (
    ALCHEMY_STAGES,
    DECANS,
    ELDER_FUTHARK_RUNES,
    GOLDEN_DAWN_GRADES,
    I_CHING_HEXAGRAMS,
    MASTER_NUMBERS,
    NUMEROLOGY_NUMBERS,
    SEVEN_RAYS,
    TAROT_COURTS,
    TAROT_MAJORS,
    TAROT_SPREADS,
    TREE_OF_LIFE_PATHS,
    TREE_OF_LIFE_SEPHIROTH,
)


def test_tree_of_life_tables():
    assert len(TREE_OF_LIFE_SEPHIROTH) == 10
    assert len(TREE_OF_LIFE_PATHS) == 22
    # Ensure paths link valid sephiroth numbers
    sephira_numbers = {item.number for item in TREE_OF_LIFE_SEPHIROTH}
    for path in TREE_OF_LIFE_PATHS:
        assert set(path.connects).issubset(sephira_numbers)


def test_alchemy_sequence_order():
    assert len(ALCHEMY_STAGES) == 7
    assert ALCHEMY_STAGES[0].name == "Calcination"
    assert ALCHEMY_STAGES[-1].name == "Coagulation"


def test_seven_rays():
    assert len(SEVEN_RAYS) == 7
    assert SEVEN_RAYS[0].color == "Red"


def test_golden_dawn_grades():
    titles = [grade.title for grade in GOLDEN_DAWN_GRADES]
    assert "Adeptus Minor" in titles
    assert any(grade.grade == "Portal" for grade in GOLDEN_DAWN_GRADES)


def test_tarot_expansions():
    assert len(TAROT_MAJORS) == 22
    assert TAROT_MAJORS[0].name == "The Fool"
    assert len(TAROT_COURTS) == 16
    assert len(TAROT_SPREADS) == 3


def test_numerology_tables():
    assert len(NUMEROLOGY_NUMBERS) == 10  # digits 0–9
    assert NUMEROLOGY_NUMBERS[1].value == 1
    master_values = {entry.value for entry in MASTER_NUMBERS}
    assert {11, 22, 33}.issubset(master_values)


def test_oracular_collections():
    assert len(I_CHING_HEXAGRAMS) == 64
    assert I_CHING_HEXAGRAMS[0].translation == "The Creative"
    assert len(ELDER_FUTHARK_RUNES) == 24
    assert ELDER_FUTHARK_RUNES[0].name == "Fehu"


def test_decans_still_available():
    assert len(DECANS) == 36
