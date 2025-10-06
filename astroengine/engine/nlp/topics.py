"""Topic grouping helpers."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass
class Topic:
    name: str
    keywords: Sequence[str]


class KeywordTopicModel:
    """Cluster notes using the most frequent keywords."""

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k

    def fit_transform(self, documents: Iterable[str]) -> list[Topic]:
        counter: Counter[str] = Counter()
        for document in documents:
            for token in self._tokenise(document):
                counter[token] += 1
        topics: list[Topic] = []
        for keyword, _ in counter.most_common(self.top_k):
            topics.append(Topic(name=keyword, keywords=[keyword]))
        return topics

    @staticmethod
    def _tokenise(text: str) -> list[str]:
        return [token.strip(".,!?;:").lower() for token in text.split() if token]


def describe_topics(documents: Iterable[str], top_k: int = 5) -> list[Topic]:
    return KeywordTopicModel(top_k=top_k).fit_transform(documents)
