"""Vision ingestion helpers for parsing chart screenshots."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


DATE_PATTERN = re.compile(r"(?P<month>\w+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})", re.I)
TIME_PATTERN = re.compile(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm)?", re.I)
POSITION_PATTERN = re.compile(r"(?P<body>[A-Za-z]+)\s+(?P<deg>\d{1,2})°(?P<min>\d{1,2})'\s+(?P<sign>[A-Za-z]+)")


@dataclass
class VisionParseResult:
    fields: Dict[str, str]
    confidence: float
    raw_lines: List[str]


class ChartVisionParser:
    def parse(self, text: str) -> Optional[VisionParseResult]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        fields: Dict[str, str] = {}
        confidence = 0.2
        for line in lines:
            if "house system" in line.lower():
                fields["house_system"] = line.split(":", 1)[-1].strip()
                confidence += 0.1
            if match := DATE_PATTERN.search(line):
                fields["date"] = " ".join(match.groups())
                confidence += 0.2
            if match := TIME_PATTERN.search(line):
                hour = int(match.group("hour"))
                minute = match.group("minute")
                ampm = match.group("ampm")
                fields["time"] = f"{hour:02d}:{minute}{(' ' + ampm.upper()) if ampm else ''}".strip()
                confidence += 0.2
            if "tz" in line.lower() or "utc" in line.lower():
                fields["timezone"] = line.split(":", 1)[-1].strip()
                confidence += 0.1
        if any(POSITION_PATTERN.search(line) for line in lines):
            fields.setdefault("positions", "present")
            confidence += 0.2
        confidence = min(confidence, 0.99)
        return VisionParseResult(fields=fields, confidence=round(confidence, 2), raw_lines=lines)
