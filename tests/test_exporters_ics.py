from astroengine.exporters_ics import canonical_events_to_ics, write_ics_canonical


def test_canonical_events_to_ics_roundtrip(tmp_path):
    events = [
        {
            "ts": "2024-01-01T00:00:00Z",
            "moving": "Sun",
            "target": "natal_Moon",
            "aspect": "conjunction",
            "orb": 0.0,
            "applying": True,
            "score": 1.0,
            "meta": {"note": "test"},
        }
    ]

    ics_text = canonical_events_to_ics(events, calendar_name="Test Calendar")
    assert "BEGIN:VCALENDAR" in ics_text
    assert "SUMMARY:Sun conjunction natal_Moon" in ics_text

    path = tmp_path / "events.ics"
    rows = write_ics_canonical(path, events, calendar_name="Test Calendar")
    assert rows == 1
    saved = path.read_text()
    assert "Test Calendar" in saved
    assert "BEGIN:VEVENT" in saved
