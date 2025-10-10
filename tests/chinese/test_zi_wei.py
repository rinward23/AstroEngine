from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from astroengine.chinese import PALACE_NAMES, compute_zi_wei_chart


def test_zi_wei_star_distribution() -> None:
    """Zi Wei placement follows deterministic offsets for the day branch."""

    moment = datetime(1984, 2, 5, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    chart = compute_zi_wei_chart(moment)

    assert chart.life_palace_index == 7
    assert chart.body_palace_index == 11
    assert chart.palaces[chart.life_palace_index].branch.name == "Wei"
    assert chart.palaces[chart.body_palace_index].branch.name == "Hai"

    by_name = chart.palace_by_name("Friends")
    assert by_name is chart.palaces[7]

    placements = {
        palace.name: {star.name for star in palace.stars} for palace in chart.palaces
    }
    assert placements["Life"] == {"Tian Liang"}
    assert placements["Children"] == {"Zi Wei"}
    assert placements["Travel"] == {"Wu Qu"}
    assert placements["Friends"] == {"Tian Tong"}
    assert placements["Parents"] == {"Tian Xiang"}

    assert chart.provenance["life_palace_branch"] == "Wei"


@pytest.mark.parametrize("name", PALACE_NAMES)
def test_palace_by_name_round_trip(name: str) -> None:
    moment = datetime(2000, 6, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    chart = compute_zi_wei_chart(moment)

    palace = chart.palace_by_name(name)
    assert palace.name == name
    assert palace in chart.palaces
