"""Mock RAG + tools — CHỈ dùng dev/test.

Thay trước khi integrate: `src/rag` (index thật) và `src/tools` (tool thật).
Contract giữ nguyên: retriever có `.retrieve(query, k) -> list[Chunk]`,
tool có `.name/.description/.signature` và gọi được bằng kwargs.
"""

from .rag import Chunk, InMemoryRetriever, NullRetriever, Retriever
from .tools import Tool, ToolRegistry, make_search_docs

__all__ = [
    "Chunk",
    "InMemoryRetriever",
    "NullRetriever",
    "Retriever",
    "Tool",
    "ToolRegistry",
    "make_search_docs",
]
