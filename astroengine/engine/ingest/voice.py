"""Voice intent parsing utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class VoiceIntent:
    intent: str
    payload: Dict[str, str]
    transcript: str


class VoiceIntentParser:
    PATTERNS = {
        "search_aspects": re.compile(r"find\s+(?P<body1>\w+)[\s-]*(?P<body2>\w+)\s+(?P<aspect>sextile|square|trine|conjunction|opposition)s?", re.I),
        "best_window": re.compile(r"best\s+(?P<duration>\d+)(?:-?hour)?\s+window\s+(?P<timeframe>next\s+week|this\s+friday|tomorrow)", re.I),
        "voc_detect": re.compile(r"voc\s+(?P<day>today|tomorrow|(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday))", re.I),
    }

    def parse(self, transcript: str) -> Optional[VoiceIntent]:
        transcript = transcript.strip()
        for intent, pattern in self.PATTERNS.items():
            match = pattern.search(transcript)
            if match:
                payload = {key: value for key, value in match.groupdict().items() if value}
                return VoiceIntent(intent=intent, payload=payload, transcript=transcript)
        if "progression" in transcript.lower():
            return VoiceIntent(intent="progression_lookup", payload={"query": transcript}, transcript=transcript)
        return None
