"""Embedding query bằng multilingual-e5-large lưu cục bộ."""

from __future__ import annotations

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "intfloat-multilingual-e5-large"
_ENCODE_LOCK = threading.Lock()


class LocalEmbeddingError(RuntimeError):
    """Model local thiếu hoặc không tạo được embedding."""


def resolve_model_path() -> Path:
    raw = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
    if not raw:
        return DEFAULT_MODEL_PATH
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def load_local_model() -> Any:
    model_path = resolve_model_path()
    if not model_path.exists():
        raise LocalEmbeddingError(
            f"Chưa có model local tại {model_path}. "
            "Tải intfloat/multilingual-e5-large trước khi chạy app."
        )
    device = os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu").strip() or "cpu"
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(
            str(model_path),
            device=device,
            local_files_only=True,
            trust_remote_code=False,
        )
    except Exception as exc:
        raise LocalEmbeddingError(f"Không nạp được model local: {exc}") from exc


def embed_query(question: str, prefix: str = "query:") -> list[float]:
    text = f"{prefix.rstrip()} {question}" if prefix else question
    model = load_local_model()
    with _ENCODE_LOCK:
        vectors = model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    vector = vectors[0].tolist()
    if len(vector) != 1024:
        raise LocalEmbeddingError(
            f"Vector local có {len(vector)} chiều; cần 1024 chiều cho multilingual-e5-large"
        )
    return [float(value) for value in vector]


def warmup_local_model() -> None:
    """Nạp weights lúc khởi động; chưa encode để tránh chậm thêm."""
    load_local_model()


__all__ = [
    "LocalEmbeddingError",
    "embed_query",
    "load_local_model",
    "resolve_model_path",
    "warmup_local_model",
]
