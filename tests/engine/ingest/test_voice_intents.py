from __future__ import annotations

from astroengine.engine.ingest.voice import VoiceIntentParser


def test_detects_aspect_search():
    parser = VoiceIntentParser()
    intent = parser.parse("Find Mars Venus sextile next three months")
    assert intent is not None
    assert intent.intent == "search_aspects"
    assert intent.payload["aspect"].lower() == "sextile"


def test_detects_voc_request():
    parser = VoiceIntentParser()
    intent = parser.parse("VOC tomorrow 9 am to 5 pm")
    assert intent is not None
    assert intent.intent == "voc_detect"
    assert intent.payload["day"].lower() == "tomorrow"


def test_handles_progression_queries():
    parser = VoiceIntentParser()
    intent = parser.parse("Show me the secondary progression for next week")
    assert intent is not None
    assert intent.intent == "progression_lookup"
