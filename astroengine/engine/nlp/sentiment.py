"""Lightweight sentiment and topic classification wrappers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

POSITIVE_TOKENS = {
    "love",
    "joy",
    "excited",
    "win",
    "grateful",
    "calm",
    "balanced",
    "support",
    "growth",
}
NEGATIVE_TOKENS = {
    "angry",
    "tired",
    "stressed",
    "loss",
    "anxious",
    "fear",
    "blocked",
    "grief",
}


@dataclass
class SentimentResult:
    label: str
    confidence: float
    backend: str


class SentimentBackend:
    def classify(self, text: str) -> SentimentResult:
        raise NotImplementedError


class RuleBasedSentimentBackend(SentimentBackend):
    """Very small keyword based sentiment classifier."""

    def __init__(self, positive_tokens: Optional[Iterable[str]] = None, negative_tokens: Optional[Iterable[str]] = None) -> None:
        self.positive_tokens = set(token.lower() for token in (positive_tokens or POSITIVE_TOKENS))
        self.negative_tokens = set(token.lower() for token in (negative_tokens or NEGATIVE_TOKENS))

    def classify(self, text: str) -> SentimentResult:
        tokens = [token.strip(".,!?;:").lower() for token in text.split()]
        positives = sum(1 for token in tokens if token in self.positive_tokens)
        negatives = sum(1 for token in tokens if token in self.negative_tokens)
        if positives > negatives:
            label = "positive"
        elif negatives > positives:
            label = "negative"
        else:
            label = "neutral"
        total = max(positives + negatives, 1)
        confidence = max(positives, negatives) / total
        return SentimentResult(label=label, confidence=confidence, backend="rule_based")


class TransformerSentimentBackend(SentimentBackend):
    """Proxy backend that allows swapping in a transformer model later."""

    def __init__(self, fallback: Optional[SentimentBackend] = None, calibrate: Optional[Callable[[float], float]] = None) -> None:
        self.fallback = fallback or RuleBasedSentimentBackend()
        self.calibrate = calibrate or (lambda score: min(max(score, 0.0), 1.0))

    def classify(self, text: str) -> SentimentResult:
        result = self.fallback.classify(text)
        adjusted = self.calibrate(result.confidence)
        return SentimentResult(label=result.label, confidence=adjusted, backend="transformer")


def classify_sentiment(text: str, backend: Optional[SentimentBackend] = None) -> SentimentResult:
    backend = backend or RuleBasedSentimentBackend()
    return backend.classify(text)
