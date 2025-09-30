from __future__ import annotations

from astroengine.engine.nlp.sentiment import RuleBasedSentimentBackend, TransformerSentimentBackend, classify_sentiment


def test_rule_based_sentiment_distinguishes_polarity():
    backend = RuleBasedSentimentBackend()
    positive = backend.classify("I feel grateful and excited about this transit")
    negative = backend.classify("I am tired and anxious today")
    assert positive.label == "positive"
    assert negative.label == "negative"


def test_transformer_backend_applies_calibration():
    backend = TransformerSentimentBackend(calibrate=lambda score: score * 0.5)
    result = backend.classify("I feel grateful")
    assert result.backend == "transformer"
    assert 0 <= result.confidence <= 1


def test_classify_sentiment_helper_uses_default_backend():
    result = classify_sentiment("I feel calm")
    assert result.label == "positive"
