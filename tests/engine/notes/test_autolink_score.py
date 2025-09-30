from __future__ import annotations

from datetime import datetime, timedelta, timezone

from astroengine.engine.notes.linker import AutoLinkScorer, CandidateEvent


def test_scoring_respects_severity_and_time():
    scorer = AutoLinkScorer()
    note_time = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    high = CandidateEvent(event_id="high", timestamp=note_time, severity=8, tags=("career",))
    low = CandidateEvent(event_id="low", timestamp=note_time + timedelta(hours=10), severity=2, tags=("career",))

    results = scorer.score("note", note_time, ("career",), [high, low])
    assert results[0].event_id == "high"
    assert results[0].score > results[1].score


def test_tag_bonus_applied():
    scorer = AutoLinkScorer(gamma=0.3)
    note_time = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    match = CandidateEvent(event_id="match", timestamp=note_time, severity=5, tags=("health",))
    mismatch = CandidateEvent(event_id="mismatch", timestamp=note_time, severity=5, tags=("career",))

    results = scorer.score("note", note_time, ("health",), [match, mismatch])
    assert results[0].event_id == "match"
    assert results[0].score > results[1].score
