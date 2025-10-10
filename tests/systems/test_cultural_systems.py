from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def systems_modules():
    repo_root = Path(__file__).resolve().parents[1]
    package = types.ModuleType("astroengine")
    package.__path__ = [str(repo_root / "astroengine")]
    sys.modules.setdefault("astroengine", package)

    systems_pkg = types.ModuleType("astroengine.systems")
    systems_pkg.__path__ = [str(repo_root / "astroengine" / "systems")]
    sys.modules.setdefault("astroengine.systems", systems_pkg)

    chinese = importlib.import_module("astroengine.systems.chinese")
    mayan = importlib.import_module("astroengine.systems.mayan")
    tibetan = importlib.import_module("astroengine.systems.tibetan")
    return chinese, mayan, tibetan


def test_chinese_prc_foundation(systems_modules):
    chinese, _, _ = systems_modules
    moment = datetime(1949, 10, 1, 15, 0)

    lunar = chinese.chinese_lunar_from_gregorian(moment)
    assert (lunar.year, lunar.month, lunar.day, lunar.is_leap_month) == (1949, 8, 10, False)

    pillars = chinese.four_pillars_from_moment(moment)
    assert pillars.year == ("Ji", "Chou")
    assert pillars.month == ("Gui", "You")
    assert pillars.day == ("Ren", "Xu")
    assert pillars.hour == ("Wu", "Shen")
    assert chinese.hour_branch(moment) == "Shen"


def test_chinese_leap_month_roundtrip(systems_modules):
    chinese, _, _ = systems_modules
    moment = datetime(2001, 5, 23)
    lunar = chinese.chinese_lunar_from_gregorian(moment)
    assert (lunar.year, lunar.month, lunar.day, lunar.is_leap_month) == (2001, 4, 1, True)
    assert chinese.gregorian_from_chinese_lunar(lunar) == moment.date()


def test_mayan_long_count_reaches_baktun_13(systems_modules):
    _, mayan, _ = systems_modules
    moment = datetime(2012, 12, 21)

    long_count = mayan.long_count_from_gregorian(moment)
    assert (long_count.baktun, long_count.katun, long_count.tun, long_count.uinal, long_count.kin) == (13, 0, 0, 0, 0)
    assert mayan.gregorian_from_long_count(long_count) == moment.date()

    calendar_round = mayan.calendar_round_from_gregorian(moment)
    assert (calendar_round.tzolkin_number, calendar_round.tzolkin_name) == (4, "Ajaw")
    assert (calendar_round.haab_day, calendar_round.haab_month) == (3, "K'ank'in")
    assert calendar_round.lord_of_night.startswith("G9")


def test_tibetan_rabjung_cycles(systems_modules):
    _, _, tibetan = systems_modules

    uprising = tibetan.gregorian_year_to_rabjung(1959)
    assert (uprising.cycle, uprising.year_in_cycle) == (16, 33)
    assert uprising.element == "Earth"
    assert uprising.animal == "Pig"
    assert uprising.gender == "female"
    assert uprising.parkha == "Li"
    assert uprising.mewa == 4

    present = tibetan.gregorian_year_to_rabjung(2023)
    assert (present.cycle, present.year_in_cycle) == (17, 37)
    assert present.element == "Water"
    assert present.animal == "Rabbit"
    assert present.parkha == "Li"
    assert tibetan.rabjung_to_gregorian_year(present.cycle, present.year_in_cycle) == 2023
