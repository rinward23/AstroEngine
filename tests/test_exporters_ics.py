from pathlib import Path

from astroengine.canonical import TransitEvent
from astroengine.events import ReturnEvent
from astroengine.exporters_ics import write_ics


def test_write_ics_supports_ingress_and_returns(tmp_path):
    path = Path(tmp_path) / "events.ics"
    transit = TransitEvent(
        ts="2025-08-23T10:00:00Z",
        moving="Mars",
        target="natal_Mercury",
        aspect="square",
        orb=0.2,
        applying=False,
        score=1.5,
        meta={"event_type": "ingress", "ingress_sign": "Virgo", "natal_id": "n100"},
    )
    solar_return = ReturnEvent(
        ts="2025-07-10T05:00:00Z",
        jd=2457210.5,
        body="Sun",
        method="solar",
        longitude=123.456,
    )

    count = write_ics(
        path,
        [transit, solar_return],
        calendar_name="AstroEngine QA",
        summary_template="{label} [{natal_id}]",
        description_template="Score={score_label}|Lon={longitude}",
    )
    assert count == 2

    payload = path.read_text()
    assert "X-WR-CALNAME:AstroEngine QA" in payload
    assert "SUMMARY:Mars ingress Virgo [n100]" in payload
    assert "SUMMARY:Sun Solar return [unknown]" in payload
    assert "DESCRIPTION:Score=1.50|Lon=" in payload
