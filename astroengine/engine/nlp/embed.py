"""Deterministic embeddings based on hashing."""
from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    text: str
    vector: list[float]


class HashingSentenceEmbedder:
    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension

    def embed(self, text: str) -> EmbeddingResult:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = self._expand_digest(digest, self.dimension)
        return EmbeddingResult(text=text, vector=vector)

    def embed_many(self, texts: Iterable[str]) -> list[EmbeddingResult]:
        return [self.embed(text) for text in texts]

    @staticmethod
    def _expand_digest(digest: bytes, dimension: int) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < dimension:
            chunk = hashlib.sha256(digest + counter.to_bytes(4, "little")).digest()
            for idx in range(0, len(chunk), 4):
                if len(values) >= dimension:
                    break
                segment = chunk[idx : idx + 4]
                value = int.from_bytes(segment, "little", signed=False)
                values.append((value % 1000) / 1000.0)
            counter += 1
        return values
