from __future__ import annotations

from astroengine.engine.ingest.vision import ChartVisionParser


def test_parser_extracts_basic_fields():
    parser = ChartVisionParser()
    text = """
    Natal Chart
    March 10, 1988  08:15 PM
    TZ: PST
    House System: Placidus
    Sun 12°34' Aries
    """
    result = parser.parse(text)
    assert result is not None
    assert result.fields["date"].startswith("March")
    assert result.fields["time"].startswith("08")
    assert result.fields["timezone"] == "PST"
    assert result.fields["house_system"].lower().startswith("placidus")
    assert result.confidence > 0.5
