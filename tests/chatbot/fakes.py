"""Test double cho retriever và tool.

Sản phẩm không còn `search_docs` (chunk đổ sẵn vào prompt), nhưng vòng ReAct vẫn
là cơ chế tổng quát chạy được với tool bất kỳ — nên test loop cần một tool giả
để bấm vào. Đây là tool đó, không phải mã sản phẩm.
"""

from src.chatbot.types import Chunk, Tool


class FakeRetriever:
    """Xếp hạng bằng keyword overlap — đủ để test, không cần ChromaDB."""

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


def make_fake_search_tool(retriever: FakeRetriever, default_k: int = 5) -> Tool:
    """Tool giả tên `search_docs` để test vòng ReAct gọi tool, xử lý lỗi, chống lặp."""

    def search_docs(query: str, k: int = default_k) -> str:
        chunks = retriever.retrieve(query, k=k)
        if not chunks:
            return "Không tìm thấy tài liệu khớp."
        return "\n\n".join(f"[{c.source}] {c.text}" for c in chunks)

    return Tool(
        name="search_docs",
        description="Tìm đoạn tài liệu liên quan tới truy vấn.",
        signature="search_docs(query: str, k: int = 5) -> str",
        func=search_docs,
    )
