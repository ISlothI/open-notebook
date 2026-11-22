"""Test doubles of the ports."""

import math
from zlib import crc32

from open_notebook.application.ports import EmbeddingUnavailableError
from open_notebook.domain.search import Vector

DIMENSIONS = 384
CONCEPT_WEIGHT = 10.0
# Words that mean the same get the same direction, which is what a real model approximates.
CONCEPTS = [{"car", "automobile", "vehicle"}, {"happy", "joyful", "glad"}, {"doctor", "physician"}]


class FakeEmbeddings:
    def __init__(self) -> None:
        self.available = True

    def embed_query(self, query: str) -> Vector:
        return self.embed_passages([query])[0]

    def embed_passages(self, passages: list[str]) -> list[Vector]:
        if not self.available:
            raise EmbeddingUnavailableError("switched off by the test")
        return [self._embed(passage) for passage in passages]

    @staticmethod
    def _embed(passage: str) -> Vector:
        words = set(passage.lower().split())
        vector = [0.0] * DIMENSIONS
        for word in words:
            vector[len(CONCEPTS) + crc32(word.encode()) % (DIMENSIONS - len(CONCEPTS))] = 1.0
        for index, concept in enumerate(CONCEPTS):
            if words & concept:
                vector[index] = CONCEPT_WEIGHT
        length = math.hypot(*vector)
        return [value / length for value in vector]
