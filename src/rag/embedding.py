"""Tạo embedding cho ``chunks.json`` và lưu vào ChromaDB local.

Chạy từ thư mục gốc dự án:

    python src/rag/embedding.py

Mặc định dữ liệu được lưu tại ``src/rag/chroma_db``. Script dùng API
OpenAI-compatible của OpenRouter và đọc cấu hình từ file ``.env`` ở thư mục
gốc dự án.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests


RAG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RAG_DIR.parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_CHUNKS_FILE = RAG_DIR / "chunks.json"
DEFAULT_CHROMA_DIR = RAG_DIR / "chroma_db"
DEFAULT_COLLECTION_NAME = "ai_thuc_chien_chunks"
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504, 524, 529}


class ConfigurationError(ValueError):
    """Cấu hình môi trường thiếu hoặc không hợp lệ."""


class EmbeddingAPIError(RuntimeError):
    """API embedding trả lỗi hoặc dữ liệu sai định dạng."""


@dataclass(frozen=True)
class EmbeddingConfig:
    api_key: str
    model: str
    base_url: str
    batch_size: int
    timeout_seconds: float
    max_retries: int
    document_prefix: str
    collection_name: str

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/embeddings"


def load_env_file(env_file: Path = DEFAULT_ENV_FILE) -> None:
    """Đọc file .env bằng thư viện chuẩn, không ghi đè biến môi trường có sẵn."""

    if not env_file.exists():
        raise ConfigurationError(f"Không tìm thấy file cấu hình: {env_file}")

    for line_number, raw_line in enumerate(
        env_file.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigurationError(
                f"Dòng {line_number} trong {env_file} không có dấu '='"
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigurationError(
                f"Dòng {line_number} trong {env_file} thiếu tên biến"
            )
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Thiếu biến {name} trong .env")
    return value


def positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} phải là số nguyên") from exc
    if value < 1:
        raise ConfigurationError(f"{name} phải lớn hơn 0")
    return value


def positive_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} phải là số") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} phải lớn hơn 0")
    return value


def load_config(
    env_file: Path = DEFAULT_ENV_FILE,
    require_api_key: bool = True,
) -> EmbeddingConfig:
    load_env_file(env_file)
    api_key = os.getenv("EMBEDDING_API", "").strip()
    if require_api_key and not api_key:
        raise ConfigurationError("Thiếu biến EMBEDDING_API trong .env")
    if api_key and "..." in api_key:
        raise ConfigurationError(
            "EMBEDDING_API đang là khóa rút gọn có '...'. "
            "Hãy thay bằng API key đầy đủ trong .env."
        )

    base_url = os.getenv(
        "EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1"
    ).strip()
    if not base_url.startswith(("https://", "http://")):
        raise ConfigurationError("EMBEDDING_BASE_URL phải bắt đầu bằng http:// hoặc https://")

    return EmbeddingConfig(
        api_key=api_key,
        model=required_env("EMBEDDING_MODEL"),
        base_url=base_url,
        batch_size=positive_int_env("EMBEDDING_BATCH_SIZE", 8),
        timeout_seconds=positive_float_env("EMBEDDING_TIMEOUT_SECONDS", 60.0),
        max_retries=positive_int_env("EMBEDDING_MAX_RETRIES", 4),
        document_prefix=os.getenv("EMBEDDING_DOCUMENT_PREFIX", "passage:").strip(),
        collection_name=os.getenv(
            "CHROMA_COLLECTION", DEFAULT_COLLECTION_NAME
        ).strip()
        or DEFAULT_COLLECTION_NAME,
    )


def resolve_project_path(value: str | Path, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_chunks(chunks_file: Path) -> list[dict[str, Any]]:
    """Đọc và kiểm tra schema do chunking.py tạo."""

    if not chunks_file.exists():
        raise FileNotFoundError(f"Không tìm thấy chunks JSON: {chunks_file}")

    try:
        payload = json.loads(chunks_file.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON không hợp lệ: {chunks_file}: {exc}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("chunks"), list):
        raise ValueError("chunks.json phải có object gốc và field 'chunks' dạng list")

    chunks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_chunk in enumerate(payload["chunks"]):
        if not isinstance(raw_chunk, dict):
            raise ValueError(f"Chunk {index} phải là object")
        chunk_id = raw_chunk.get("id")
        content = raw_chunk.get("content")
        metadata = raw_chunk.get("metadata")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"Chunk {index} thiếu id")
        if chunk_id in seen_ids:
            raise ValueError(f"Chunk id bị trùng: {chunk_id}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Chunk {chunk_id} thiếu content")
        if not isinstance(metadata, dict):
            raise ValueError(f"Chunk {chunk_id} thiếu metadata")
        seen_ids.add(chunk_id)
        chunks.append(raw_chunk)

    if not chunks:
        raise ValueError("chunks.json không có chunk nào")
    return chunks


def batches(items: Sequence[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def prefixed_text(text: str, prefix: str) -> str:
    if not prefix:
        return text
    return f"{prefix.rstrip()} {text}"


def short_api_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:300] or "Không có nội dung lỗi"

    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        if message:
            return str(message)[:300]
    if error:
        return str(error)[:300]
    return str(body)[:300]


def parse_embeddings(payload: Any, expected_count: int) -> list[list[float]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise EmbeddingAPIError("API response thiếu field 'data' dạng list")

    data = payload["data"]
    if len(data) != expected_count:
        raise EmbeddingAPIError(
            f"API trả {len(data)} vectors, cần {expected_count} vectors"
        )

    if all(isinstance(item, dict) and isinstance(item.get("index"), int) for item in data):
        data = sorted(data, key=lambda item: item["index"])

    vectors: list[list[float]] = []
    dimensions: set[int] = set()
    for index, item in enumerate(data):
        vector = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(vector, list) or not vector:
            raise EmbeddingAPIError(f"Vector {index} không hợp lệ")
        try:
            numeric_vector = [float(value) for value in vector]
        except (TypeError, ValueError) as exc:
            raise EmbeddingAPIError(f"Vector {index} chứa giá trị không phải số") from exc
        dimensions.add(len(numeric_vector))
        vectors.append(numeric_vector)

    if len(dimensions) != 1:
        raise EmbeddingAPIError("Các vector trả về có số chiều khác nhau")
    return vectors


def request_embeddings(
    texts: Sequence[str],
    config: EmbeddingConfig,
    session: requests.Session,
) -> list[list[float]]:
    """Gọi batch embeddings, retry lỗi mạng và lỗi server tạm thời."""

    payload = {
        "model": config.model,
        "input": [prefixed_text(text, config.document_prefix) for text in texts],
        "encoding_format": "float",
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/vgo-k3-ai-product-hackathon",
        "X-Title": "VGO K3 AI Product Hackathon",
    }

    last_error: Exception | None = None
    for attempt in range(config.max_retries):
        try:
            response = session.post(
                config.endpoint,
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds,
            )
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.ok:
                try:
                    return parse_embeddings(response.json(), expected_count=len(texts))
                except ValueError as exc:
                    raise EmbeddingAPIError("API response không phải JSON hợp lệ") from exc

            message = short_api_error(response)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise EmbeddingAPIError(f"API {response.status_code}: {message}")
            last_error = EmbeddingAPIError(f"API {response.status_code}: {message}")

        if attempt + 1 < config.max_retries:
            time.sleep(min(2**attempt, 8))

    raise EmbeddingAPIError(
        f"Gọi embedding API thất bại sau {config.max_retries} lần: {last_error}"
    )


def chroma_metadata(metadata: dict[str, Any], model: str) -> dict[str, Any]:
    """Đổi metadata JSON thành các kiểu Chroma hỗ trợ."""

    result: dict[str, Any] = {"embedding_model": model}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            result[str(key)] = value
        elif isinstance(value, list) and all(
            isinstance(item, (str, int, float, bool)) for item in value
        ):
            result[str(key)] = value
        else:
            result[str(key)] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return result


def open_collection(chroma_dir: Path, config: EmbeddingConfig, recreate: bool):
    """Mở collection persistent, chặn trộn vector từ hai model khác nhau."""

    import chromadb
    from chromadb.config import Settings
    from chromadb.errors import NotFoundError

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )

    if recreate:
        try:
            client.delete_collection(config.collection_name)
        except NotFoundError:
            pass

    try:
        collection = client.get_collection(
            name=config.collection_name,
            embedding_function=None,
        )
    except NotFoundError:
        collection = client.create_collection(
            name=config.collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"embedding_model": config.model},
            embedding_function=None,
        )

    stored_model = (collection.metadata or {}).get("embedding_model")
    if stored_model and stored_model != config.model:
        raise ConfigurationError(
            f"Collection đang dùng model '{stored_model}', nhưng .env dùng "
            f"'{config.model}'. Chạy với --recreate hoặc đổi CHROMA_COLLECTION."
        )
    return collection


def build_chroma_database(
    chunks: Sequence[dict[str, Any]],
    chroma_dir: Path,
    config: EmbeddingConfig,
    recreate: bool = False,
) -> int:
    collection = open_collection(chroma_dir, config, recreate=recreate)
    total_batches = (len(chunks) + config.batch_size - 1) // config.batch_size

    with requests.Session() as session:
        for batch_index, batch in enumerate(
            batches(chunks, config.batch_size), start=1
        ):
            documents = [str(chunk["content"]) for chunk in batch]
            embeddings = request_embeddings(documents, config, session)
            collection.upsert(
                ids=[str(chunk["id"]) for chunk in batch],
                documents=documents,
                embeddings=embeddings,
                metadatas=[
                    chroma_metadata(chunk["metadata"], config.model) for chunk in batch
                ],
            )
            print(
                f"Batch {batch_index}/{total_batches}: stored {len(batch)} chunks"
            )

    return collection.count()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embedding chunks.json và lưu vào ChromaDB local."
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--chunks-file", type=Path, default=None)
    parser.add_argument("--chroma-dir", type=Path, default=None)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Xóa collection cũ cùng tên trước khi embedding lại.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Chỉ kiểm tra chunks.json; không gọi API và không tạo ChromaDB.",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    load_env_file(args.env_file)
    chunks_file = resolve_project_path(
        args.chunks_file or os.getenv("CHUNKS_FILE", ""),
        DEFAULT_CHUNKS_FILE,
    )
    chroma_dir = resolve_project_path(
        args.chroma_dir or os.getenv("CHROMA_DIR", ""),
        DEFAULT_CHROMA_DIR,
    )
    chunks = load_chunks(chunks_file)

    if args.validate_only:
        print(f"Hợp lệ: {len(chunks)} chunks trong {chunks_file.resolve()}")
        return

    config = load_config(args.env_file)
    stored_count = build_chroma_database(
        chunks=chunks,
        chroma_dir=chroma_dir,
        config=config,
        recreate=args.recreate,
    )
    print(
        f"Hoàn tất: collection '{config.collection_name}' có {stored_count} records "
        f"tại {chroma_dir.resolve()}"
    )


if __name__ == "__main__":
    try:
        main()
    except (ConfigurationError, EmbeddingAPIError, FileNotFoundError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
