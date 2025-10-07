"""API facade for running NLP correlation analyses."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from astroengine.engine.nlp.correlate import (
    CorrelationSummary,
    EventSample,
    LogisticRegressionResult,
    NoteSample,
    align_samples,
    logistic_regression,
    point_biserial,
)


@dataclass
class NLPRequest:
    notes: list[NoteSample]
    events: list[EventSample]
    window_hours: float = 36.0


@dataclass
class NLPResponse:
    correlations: list[CorrelationSummary]
    regression: list[LogisticRegressionResult]


class NLPAPI:
    def run(self, request: NLPRequest) -> NLPResponse:
        window = timedelta(hours=request.window_hours)
        pairs = align_samples(request.notes, request.events, window)
        correlations = point_biserial(pairs)
        regression = logistic_regression(pairs)
        return NLPResponse(correlations=correlations, regression=regression)
