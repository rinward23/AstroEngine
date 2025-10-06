from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

from astroengine.api.nlp import NLPAPI, NLPRequest
from astroengine.engine.nlp.correlate import EventSample, NoteSample


def build_samples():
    base = datetime(2024, 1, 1, tzinfo=UTC)
    notes = [
        NoteSample(note_id="n1", timestamp=base, sentiment=1.0, topic="growth"),
        NoteSample(note_id="n2", timestamp=base + timedelta(hours=12), sentiment=0.0, topic="growth"),
        NoteSample(note_id="n3", timestamp=base + timedelta(days=1), sentiment=0.0, topic="stress"),
        NoteSample(note_id="n4", timestamp=base + timedelta(days=1, hours=4), sentiment=1.0, topic="career"),
    ]
    events = [
        EventSample(event_id="e1", timestamp=base, feature=1.0, family="benefic"),
        EventSample(event_id="e2", timestamp=base + timedelta(hours=10), feature=0.5, family="benefic"),
        EventSample(event_id="e3", timestamp=base + timedelta(days=1), feature=-1.0, family="malefic"),
    ]
    return notes, events


def test_nlp_api_produces_correlations_and_regression():
    api = NLPAPI()
    notes, events = build_samples()
    response = api.run(NLPRequest(notes=notes, events=events))
    assert response.correlations
    assert response.regression
    benefic = next(item for item in response.correlations if item.feature == "benefic")
    assert benefic.sample_size >= 2
