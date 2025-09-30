"""API endpoints for the ingest surface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from astroengine.engine.ingest.voice import VoiceIntent, VoiceIntentParser
from astroengine.engine.ingest.vision import ChartVisionParser, VisionParseResult


@dataclass
class VoiceIngestResponse:
    transcript: str
    intent: Optional[VoiceIntent]


@dataclass
class VisionIngestResponse:
    result: Optional[VisionParseResult]


class IngestAPI:
    def __init__(self, voice_parser: Optional[VoiceIntentParser] = None, vision_parser: Optional[ChartVisionParser] = None) -> None:
        self.voice_parser = voice_parser or VoiceIntentParser()
        self.vision_parser = vision_parser or ChartVisionParser()

    def ingest_voice(self, transcript: str) -> VoiceIngestResponse:
        intent = self.voice_parser.parse(transcript)
        return VoiceIngestResponse(transcript=transcript, intent=intent)

    def ingest_vision(self, text: str) -> VisionIngestResponse:
        result = self.vision_parser.parse(text)
        return VisionIngestResponse(result=result)
