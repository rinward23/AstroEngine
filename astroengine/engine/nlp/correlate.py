"""Correlation utilities for diary entries and astro events."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class NoteSample:
    note_id: str
    timestamp: datetime
    sentiment: float
    topic: str


@dataclass
class EventSample:
    event_id: str
    timestamp: datetime
    feature: float
    family: str


@dataclass
class CorrelationSummary:
    feature: str
    coefficient: float
    sample_size: int


@dataclass
class LogisticRegressionResult:
    feature: str
    weight: float
    intercept: float


def align_samples(notes: Sequence[NoteSample], events: Sequence[EventSample], window: timedelta) -> list[tuple[NoteSample, EventSample]]:
    pairs: list[tuple[NoteSample, EventSample]] = []
    for note in notes:
        for event in events:
            if abs((event.timestamp - note.timestamp).total_seconds()) <= window.total_seconds():
                pairs.append((note, event))
    return pairs


def point_biserial(pairs: Sequence[tuple[NoteSample, EventSample]]) -> list[CorrelationSummary]:
    buckets: dict[str, list[tuple[float, float]]] = {}
    for note, event in pairs:
        buckets.setdefault(event.family, []).append((note.sentiment, event.feature))
    summaries: list[CorrelationSummary] = []
    for family, samples in buckets.items():
        sentiments = [sentiment for sentiment, _ in samples]
        features = [feature for _, feature in samples]
        coefficient = _pearson(sentiments, features)
        summaries.append(CorrelationSummary(feature=family, coefficient=coefficient, sample_size=len(samples)))
    return summaries


def logistic_regression(pairs: Sequence[tuple[NoteSample, EventSample]], lr: float = 0.1, epochs: int = 120) -> list[LogisticRegressionResult]:
    weights: dict[str, float] = {}
    intercept = 0.0
    for _ in range(epochs):
        grad_w: dict[str, float] = {}
        grad_b = 0.0
        for note, event in pairs:
            prediction = _sigmoid(weights.get(event.family, 0.0) * event.feature + intercept)
            error = note.sentiment - prediction
            grad_w[event.family] = grad_w.get(event.family, 0.0) + error * event.feature
            grad_b += error
        for family, grad in grad_w.items():
            weights[family] = weights.get(family, 0.0) + lr * grad / max(len(pairs), 1)
        intercept += lr * grad_b / max(len(pairs), 1)
    return [LogisticRegressionResult(feature=family, weight=weight, intercept=intercept) for family, weight in sorted(weights.items())]


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))
