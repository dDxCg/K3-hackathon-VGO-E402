"""MOCK retrieval — dev/test only. Thay bằng index thật ở src/rag khi integrate."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Chunk:
    """Một đoạn ngữ cảnh trả về từ retriever."""

    text: str
    source: str = "unknown"
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[Chunk]: ...


class NullRetriever:
    """Chưa có index thì trả rỗng, prompt tự bỏ mục Ngữ cảnh."""

    def retrieve(self, query: str, k: int = 5) -> list[Chunk]:
        return []


class InMemoryRetriever:
    """Retriever tạm bằng keyword overlap — test pipeline trước khi có vector index."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: str, k: int = 5) -> list[Chunk]:
        terms = set(query.lower().split())
        scored: list[Chunk] = []
        for chunk in self.chunks:
            overlap = len(terms & set(chunk.text.lower().split()))
            if overlap:
                scored.append(
                    Chunk(
                        text=chunk.text,
                        source=chunk.source,
                        score=overlap / max(len(terms), 1),
                        metadata=chunk.metadata,
                    )
                )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]
