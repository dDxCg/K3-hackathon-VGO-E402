"""Adapter RAG cho chatbot: Chroma chính, lexical fallback khi API chậm."""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from src.chatbot.mock.rag import Chunk

from . import embedding
from .local_embedding import LocalEmbeddingError
from .retrieval import DEFAULT_ENV_FILE, RetrievalError, retrieve

DEFAULT_CHUNKS_FILE = Path(__file__).resolve().parent / "chunks.json"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "ai", "bao", "ban", "cua", "co", "em", "gi", "khong", "la", "minh",
    "mot", "nhung", "o", "the", "thi", "toi", "trong", "va", "ve",
}


def _terms(text: str) -> set[str]:
    plain = _plain(text)
    return {token for token in TOKEN_RE.findall(plain) if token not in STOP_WORDS and len(token) > 1}


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _domain_bonus(query: str, content: str) -> float:
    """Rewrite nhỏ cho các intent demo mà lexical overlap thường hiểu sai."""
    bonus = 0.0
    if ("thoi luong" in query or "bao lau" in query) and (
        "12 tuan" in content or "lo trinh" in content
    ):
        bonus += 0.5
    if "ho so" in query and ("ho so dang ky" in content or "portfolio" in content):
        bonus += 0.4
    if ("dia diem" in query or "o dau" in query) and (
        "dia diem" in content or "dia chi dao tao" in content or "co so dao tao" in content
    ):
        bonus += 0.5
    return bonus


class LexicalRetriever:
    """Fallback cục bộ, không gọi mạng; dùng overlap từ khóa trên chunks.json."""

    def __init__(self, chunks_file: Path = DEFAULT_CHUNKS_FILE) -> None:
        payload = json.loads(chunks_file.read_text(encoding="utf-8-sig"))
        self.records = list(payload["chunks"])
        self._document_terms = [_terms(str(item["content"])) for item in self.records]
        self._plain_documents = [_plain(str(item["content"])) for item in self.records]
        self._heading_terms = [
            _terms(
                " ".join(
                    str(item["metadata"].get(key) or "")
                    for key in ("muc_lon", "muc_nho", "muc_con")
                )
            )
            for item in self.records
        ]

    def retrieve(self, query: str, k: int = 5) -> list[Chunk]:
        query_terms = _terms(query)
        plain_query = _plain(query)
        if not query_terms:
            return []
        scored: list[tuple[float, float, int]] = []
        for index, document_terms in enumerate(self._document_terms):
            overlap = len(query_terms & document_terms) / len(query_terms)
            domain_bonus = _domain_bonus(plain_query, self._plain_documents[index])
            if overlap >= 0.5 or domain_bonus:
                heading_overlap = len(query_terms & self._heading_terms[index]) / len(query_terms)
                official_bonus = 0.08 if self.records[index]["metadata"].get("loai_nguon") == "web" else 0.0
                rank_score = (
                    overlap
                    + 0.35 * heading_overlap
                    + official_bonus
                    + domain_bonus
                )
                calibrated_overlap = max(overlap, 0.5 if domain_bonus else 0.0)
                scored.append((rank_score, calibrated_overlap, index))
        scored.sort(key=lambda item: item[0], reverse=True)

        chunks: list[Chunk] = []
        for _, overlap, index in scored[: min(k, 3)]:
            item = self.records[index]
            metadata = dict(item["metadata"])
            metadata["chunk_id"] = item["id"]
            metadata["retrieval_mode"] = "lexical_fallback"
            # Ngưỡng 0.7 vốn dành cho cosine. Chỉ map lexical thành grounded
            # khi ít nhất nửa từ khóa có mặt trong chunk.
            score = min(0.95, 0.65 + 0.3 * overlap)
            chunks.append(
                Chunk(
                    text=str(item["content"]),
                    source=str(item["id"]),
                    score=round(score, 6),
                    metadata=metadata,
                )
            )
        return chunks


class ChromaRetriever:
    """Retriever production dùng embedding API và ChromaDB cục bộ."""

    def __init__(
        self,
        env_file: Path = DEFAULT_ENV_FILE,
        fallback: LexicalRetriever | None = None,
    ) -> None:
        self.env_file = env_file
        self.fallback = fallback or LexicalRetriever()
        self.timeout_seconds = float(os.getenv("DEMO_EMBEDDING_TIMEOUT_SECONDS", "5"))
        self.max_retries = int(os.getenv("DEMO_EMBEDDING_MAX_RETRIES", "1"))
        self.embedding_available = True
        self._cache: dict[tuple[str, int], list[Chunk]] = {}

    def retrieve(self, query: str, k: int = 5) -> list[Chunk]:
        cache_key = (query.strip().lower(), k)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        if not self.embedding_available:
            chunks = self.fallback.retrieve(query, k=k)
            self._cache[cache_key] = chunks
            return list(chunks)
        try:
            payload = retrieve(
                query,
                top_k=k,
                env_file=self.env_file,
                timeout_seconds=self.timeout_seconds,
                max_retries=self.max_retries,
            )
        except (
            RetrievalError,
            LocalEmbeddingError,
            embedding.ConfigurationError,
            embedding.EmbeddingAPIError,
        ) as exc:
            self.embedding_available = False
            print(
                f"Embedding chưa phản hồi trong giới hạn demo; dùng lexical fallback: {exc}",
                file=sys.stderr,
                flush=True,
            )
            chunks = self.fallback.retrieve(query, k=k)
            self._cache[cache_key] = chunks
            return list(chunks)
        chunks: list[Chunk] = []
        for item in payload["results"]:
            metadata = dict(item["metadata"])
            metadata["chunk_id"] = item["id"]
            chunks.append(
                Chunk(
                    text=item["content"],
                    source=item["id"],
                    score=float(item["cosine_similarity"]),
                    metadata=metadata,
                )
            )
        self._cache[cache_key] = chunks
        return list(chunks)


__all__ = ["ChromaRetriever", "LexicalRetriever"]
