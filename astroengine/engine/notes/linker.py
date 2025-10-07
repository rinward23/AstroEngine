"""Autolinking helpers for connecting notes to astro events."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CandidateEvent:
    event_id: str
    timestamp: datetime
    severity: float
    tags: Sequence[str]


@dataclass
class SuggestedLink:
    note_id: str
    event_id: str
    score: float
    source: str = "suggested"


class AutoLinkScorer:
    """Score potential links between notes and events."""

    def __init__(self, alpha: float = 0.6, beta: float = 0.3, gamma: float = 0.1, window: timedelta = timedelta(hours=36)) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.window = window

    def score(self, note_id: str, note_time: datetime, note_tags: Sequence[str], events: Iterable[CandidateEvent]) -> list[SuggestedLink]:
        note_tag_set = set(note_tags)
        links: list[SuggestedLink] = []
        for event in events:
            time_delta = abs((event.timestamp - note_time).total_seconds())
            if time_delta > self.window.total_seconds():
                continue
            time_component = 1.0 - (time_delta / self.window.total_seconds())
            tag_overlap = len(note_tag_set.intersection(set(event.tags)))
            tag_bonus = 0.0
            if note_tag_set and event.tags:
                tag_bonus = (tag_overlap / max(len(note_tag_set), 1))
            score = self.alpha * self._normalise_severity(event.severity)
            score += self.beta * max(time_component, 0.0)
            score += self.gamma * tag_bonus
            if score <= 0:
                continue
            links.append(SuggestedLink(note_id=note_id, event_id=event.event_id, score=round(score, 4)))
        links.sort(key=lambda link: link.score, reverse=True)
        return links

    @staticmethod
    def _normalise_severity(value: float) -> float:
        return max(min(value, 10.0), -10.0) / 10.0
