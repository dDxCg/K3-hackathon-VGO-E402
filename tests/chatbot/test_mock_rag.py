"""Mock retriever — dev/test only, nhưng contract phải giữ khi thay bằng index thật."""

import dataclasses

import pytest

from src.chatbot.mock.rag import Chunk, InMemoryRetriever, NullRetriever


def test_null_retriever_luon_rong():
    assert NullRetriever().retrieve("bat ky", k=5) == []


def test_chunk_la_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Chunk("x", "a.md").text = "y"  # type: ignore[misc]


def test_khong_khop_thi_rong(retriever: InMemoryRetriever):
    assert retriever.retrieve("zzz qqq") == []


def test_xep_hang_theo_overlap_giam_dan(retriever: InMemoryRetriever):
    got = retriever.retrieve("CP3 luc 16:00 ngay 1")
    assert got[0].source == "rubric.md"
    assert "CP3" in got[0].text
    assert all(a.score >= b.score for a, b in zip(got, got[1:]))


def test_k_cat_dung_so_luong(retriever: InMemoryRetriever):
    assert len(retriever.retrieve("ngay 1", k=1)) == 1


def test_score_chuan_hoa_theo_so_tu_truy_van():
    r = InMemoryRetriever([Chunk("alpha beta", "a.md")])
    assert r.retrieve("alpha beta")[0].score == pytest.approx(1.0)
    assert r.retrieve("alpha gamma")[0].score == pytest.approx(0.5)


def test_giu_nguyen_source_va_metadata():
    r = InMemoryRetriever([Chunk("alpha", "a.md", metadata={"page": 3})])
    got = r.retrieve("alpha")[0]
    assert got.source == "a.md"
    assert got.metadata == {"page": 3}
