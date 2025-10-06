"""API endpoints for the ingest surface."""
from __future__ import annotations

from dataclasses import dataclass

from astroengine.engine.ingest.vision import ChartVisionParser, VisionParseResult
from astroengine.engine.ingest.voice import VoiceIntent, VoiceIntentParser


@dataclass
class VoiceIngestResponse:
    transcript: str
    intent: VoiceIntent | None


@dataclass
class VisionIngestResponse:
    result: VisionParseResult | None


class IngestAPI:
    def __init__(self, voice_parser: VoiceIntentParser | None = None, vision_parser: ChartVisionParser | None = None) -> None:
        self.voice_parser = voice_parser or VoiceIntentParser()
        self.vision_parser = vision_parser or ChartVisionParser()

    def ingest_voice(self, transcript: str) -> VoiceIngestResponse:
        intent = self.voice_parser.parse(transcript)
        return VoiceIngestResponse(transcript=transcript, intent=intent)

    def ingest_vision(self, text: str) -> VisionIngestResponse:
        result = self.vision_parser.parse(text)
        return VisionIngestResponse(result=result)
