from types import SimpleNamespace

import pytest

from src.rag import embedding, retrieval


class FakeVector:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class FakeModel:
    def __init__(self, dimensions=1024):
        self.dimensions = dimensions
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(SimpleNamespace(texts=texts, kwargs=kwargs))
        return [FakeVector([0.0] * self.dimensions) for _ in texts]


def test_embed_documents_uses_passage_prefix_and_normalization(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(embedding, "load_local_model", lambda: model)

    vectors = embedding.embed_documents(["Nội dung A", "Nội dung B"], batch_size=2)

    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    call = model.calls[0]
    assert call.texts == ["passage: Nội dung A", "passage: Nội dung B"]
    assert call.kwargs["normalize_embeddings"] is True
    assert call.kwargs["batch_size"] == 2


def test_embed_query_uses_query_prefix(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(embedding, "load_local_model", lambda: model)

    vector = embedding.embed_query("Học bao lâu?")

    assert len(vector) == 1024
    assert model.calls[0].texts == ["query: Học bao lâu?"]


def test_embed_texts_rejects_wrong_dimension(monkeypatch):
    monkeypatch.setattr(embedding, "load_local_model", lambda: FakeModel(3))

    with pytest.raises(embedding.LocalEmbeddingError, match="1024"):
        embedding.embed_query("Câu hỏi")


def test_retrieval_query_uses_embedding_module(monkeypatch):
    seen = {}

    def fake_embed_query(question, prefix):
        seen.update(question=question, prefix=prefix)
        return [0.0] * 1024

    monkeypatch.setattr(embedding, "embed_query", fake_embed_query)
    monkeypatch.setenv("EMBEDDING_QUERY_PREFIX", "query:")

    vector = retrieval.query_embedding("Hồ sơ gồm gì?")

    assert len(vector) == 1024
    assert seen == {"question": "Hồ sơ gồm gì?", "prefix": "query:"}
