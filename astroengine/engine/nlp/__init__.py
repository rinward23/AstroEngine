"""NLP pipelines for correlating diary content with events."""

from .correlate import (
    CorrelationSummary,
    EventSample,
    LogisticRegressionResult,
    NoteSample,
    align_samples,
    logistic_regression,
    point_biserial,
)
from .embed import EmbeddingResult, HashingSentenceEmbedder
from .sentiment import (
    RuleBasedSentimentBackend,
    SentimentBackend,
    SentimentResult,
    TransformerSentimentBackend,
    classify_sentiment,
)
from .topics import KeywordTopicModel, Topic, describe_topics

__all__ = [
    "CorrelationSummary",
    "EventSample",
    "LogisticRegressionResult",
    "NoteSample",
    "align_samples",
    "logistic_regression",
    "point_biserial",
    "EmbeddingResult",
    "HashingSentenceEmbedder",
    "RuleBasedSentimentBackend",
    "SentimentBackend",
    "SentimentResult",
    "TransformerSentimentBackend",
    "classify_sentiment",
    "KeywordTopicModel",
    "Topic",
    "describe_topics",
]
