from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from astroengine.chinese import compute_four_pillars


def test_four_pillars_known_example() -> None:
    """BaZi pillars match published Jia-Zi era almanac values."""

    moment = datetime(1984, 2, 5, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    chart = compute_four_pillars(moment)

    assert chart.pillars["year"].stem.name == "Jia"
    assert chart.pillars["year"].branch.name == "Zi"
    assert chart.pillars["month"].stem.name == "Bing"
    assert chart.pillars["month"].branch.name == "Yin"
    assert chart.pillars["day"].stem.name == "Ding"
    assert chart.pillars["day"].branch.name == "Mao"
    assert chart.pillars["hour"].stem.name == "Yi"
    assert chart.pillars["hour"].branch.name == "Si"

    labels = [pillar.label() for pillar in chart.ordered_pillars()]
    assert labels == ["Jia-Zi", "Bing-Yin", "Ding-Mao", "Yi-Si"]


def test_four_pillars_timezone_override() -> None:
    """Explicit timezone overrides align with aware datetime inputs."""

    naive = datetime(1991, 8, 17, 3, 45)
    tz = ZoneInfo("Asia/Shanghai")
    aware = naive.replace(tzinfo=tz)

    chart_naive = compute_four_pillars(naive, timezone=tz)
    chart_aware = compute_four_pillars(aware)

    assert [p.label() for p in chart_naive.ordered_pillars()] == [
        p.label() for p in chart_aware.ordered_pillars()
    ]
