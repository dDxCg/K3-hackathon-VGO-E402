import json

from src.rag import embedding
from src.rag.retriever import ChromaRetriever, LexicalRetriever


def test_lexical_retriever_returns_grounded_chunk_and_metadata(tmp_path):
    chunks_file = tmp_path / "chunks.json"
    chunks_file.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "id": "chunk_schedule",
                        "content": "Lịch học gồm hai buổi tối mỗi tuần.",
                        "metadata": {"source_link": "https://example.com"},
                    },
                    {
                        "id": "chunk_other",
                        "content": "Thông tin chương trình khác.",
                        "metadata": {},
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    [chunk] = LexicalRetriever(chunks_file).retrieve("Lịch học thế nào?", k=1)
    assert chunk.source == "chunk_schedule"
    assert chunk.score >= 0.7
    assert chunk.metadata["retrieval_mode"] == "lexical_fallback"


def test_lexical_retriever_rejects_empty_or_stopword_only_query(tmp_path):
    chunks_file = tmp_path / "chunks.json"
    chunks_file.write_text('{"chunks": []}', encoding="utf-8")
    retriever = LexicalRetriever(chunks_file)
    assert retriever.retrieve("có là và không") == []


def test_chroma_timeout_opens_fallback_circuit(monkeypatch):
    class StubFallback:
        def __init__(self):
            self.calls = 0

        def retrieve(self, query, k=5):
            self.calls += 1
            return []

    primary_calls = 0

    def timeout(*args, **kwargs):
        nonlocal primary_calls
        primary_calls += 1
        raise embedding.EmbeddingAPIError("timeout")

    fallback = StubFallback()
    monkeypatch.setattr("src.rag.retriever.retrieve", timeout)
    retriever = ChromaRetriever(fallback=fallback)
    retriever.retrieve("câu một")
    retriever.retrieve("câu hai")

    assert primary_calls == 1
    assert fallback.calls == 2
    assert retriever.embedding_available is False
