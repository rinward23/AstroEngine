from datetime import UTC, datetime

from astroengine.export import Alarm, CalendarEvent, to_csv, to_ics


def _sample_event():
    return CalendarEvent(
        uid="evt-123",
        kind="transit",
        summary="Venus trine Jupiter",
        description="Facet breakdown",
        start="2025-05-02T14:20:00Z",
        end="2025-05-02T16:20:00Z",
        location="New York, NY",
        categories=("Astro", "Trine"),
        alarms=(Alarm(trigger="-PT30M"),),
        meta={"severity": 0.86, "dataset": "sf9://election/123"},
    )


def test_to_ics_emits_categories_and_alarm(tmp_path):
    events = [_sample_event()]
    stamp = datetime(2024, 1, 1, tzinfo=UTC)

    payload = to_ics(events, tz="America/New_York", calendar_name="Astro Planner", generated_ts=stamp)
    text = payload.decode("utf-8")

    assert "BEGIN:VCALENDAR" in text
    assert "X-WR-CALNAME:Astro Planner" in text
    assert "BEGIN:VTIMEZONE" in text and "TZID:America/New_York" in text
    assert "SUMMARY:Venus trine Jupiter" in text
    assert "CATEGORIES:Astro,Trine" in text
    assert "BEGIN:VALARM" in text and "TRIGGER:-PT30M" in text
    assert "X-ASTROENGINE-META:" in text
    # DTSTART should reference the requested timezone without a Z suffix
    assert "DTSTART;TZID=America/New_York:20250502T102000" in text


def test_to_csv_preserves_payload_round_trip():
    events = [_sample_event()]
    csv_bytes = to_csv(events)
    text = csv_bytes.decode("utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("uid,kind,summary")
    assert "evt-123" in lines[1]
    assert "sf9://election/123" in lines[1]


def test_multiple_events_fold_long_lines():
    long_description = "This description is extremely long " * 4
    events = [
        CalendarEvent(
            uid="evt-456",
            kind="return",
            summary="Mars return",
            description=long_description,
            start="2025-07-01T05:00:00Z",
            all_day=False,
            alarms=(Alarm(trigger="-P1D", description="Reminder"),),
            meta={"note": "Check Solar Fire"},
        )
    ]
    stamp = datetime(2024, 1, 1, tzinfo=UTC)
    payload = to_ics(events, generated_ts=stamp)
    text = payload.decode("utf-8")
    folded = [line for line in text.split("\r\n") if line.startswith(" ")]  # continuation lines
    assert folded, "Expected folded lines for long description"
    assert "DESCRIPTION:This description" in text
