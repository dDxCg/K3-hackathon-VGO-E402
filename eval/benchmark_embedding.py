"""Benchmark 10 câu hỏi: E5 local so với cùng model qua OpenRouter.

Đo riêng:
- model_load_seconds: chỉ có local, trả một lần khi khởi động process;
- embedding_seconds: thời gian tạo vector cho từng câu;
- chroma_query_seconds: thời gian Chroma tìm top-k;
- total_retrieval_seconds: embedding + Chroma query.

Không gọi chat LLM và không gửi chunk tài liệu ra ngoài. Backend API chỉ gửi
10 câu hỏi tới endpoint embeddings đã cấu hình trong .env.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Callable

import requests

from src.rag import embedding
from src.rag.local_embedding import embed_query, resolve_model_path, warmup_local_model
from src.rag.retrieval import DEFAULT_CHROMA_DIR, DEFAULT_ENV_FILE, open_existing_collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "eval" / "results"
QUESTIONS = [
    "Chương trình học trong bao lâu?",
    "Lịch học hằng ngày như thế nào?",
    "Địa điểm học ở đâu?",
    "Điều kiện dự tuyển là gì?",
    "Hồ sơ đăng ký gồm những gì?",
    "Bài đánh giá năng lực kiểm tra nội dung gì?",
    "Chương trình có những track nào?",
    "Có thể vừa học vừa đi làm không?",
    "Hạn nộp hồ sơ khóa đang tuyển là khi nào?",
    "Học viên có được hỗ trợ học phí không?",
]


@dataclass
class Measurement:
    question_index: int
    question: str
    backend: str
    embedding_model: str
    embedding_seconds: float | None
    chroma_query_seconds: float | None
    total_retrieval_seconds: float | None
    top_chunk_id: str | None
    top_similarity: float | None
    error: str | None = None
    failure_wait_seconds: float | None = None


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def summarize(rows: list[Measurement]) -> dict:
    valid = [row for row in rows if row.embedding_seconds is not None]
    embedding_times = [float(row.embedding_seconds) for row in valid]
    total_times = [
        float(row.total_retrieval_seconds)
        for row in valid
        if row.total_retrieval_seconds is not None
    ]
    attempt_times = [
        float(row.embedding_seconds)
        if row.embedding_seconds is not None
        else float(row.failure_wait_seconds)
        for row in rows
        if row.embedding_seconds is not None or row.failure_wait_seconds is not None
    ]
    return {
        "questions": len(rows),
        "successful": len(valid),
        "failed": len(rows) - len(valid),
        "embedding_mean_seconds": statistics.fmean(embedding_times) if embedding_times else None,
        "embedding_median_seconds": statistics.median(embedding_times) if embedding_times else None,
        "embedding_p95_seconds": percentile(embedding_times, 0.95) if embedding_times else None,
        "embedding_min_seconds": min(embedding_times) if embedding_times else None,
        "embedding_max_seconds": max(embedding_times) if embedding_times else None,
        "total_retrieval_mean_seconds": statistics.fmean(total_times) if total_times else None,
        "total_retrieval_median_seconds": statistics.median(total_times) if total_times else None,
        "attempt_mean_seconds": statistics.fmean(attempt_times) if attempt_times else None,
    }


def query_chroma(collection, vector: list[float], top_k: int) -> tuple[str | None, float | None]:
    raw = collection.query(
        query_embeddings=[vector],
        n_results=min(top_k, collection.count()),
        include=["distances"],
    )
    ids = (raw.get("ids") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]
    if not ids or not distances:
        return None, None
    return str(ids[0]), round(1.0 - float(distances[0]), 6)


def run_backend(
    backend: str,
    model_name: str,
    questions: list[str],
    embed: Callable[[str], list[float]],
    collection,
    top_k: int,
) -> list[Measurement]:
    rows: list[Measurement] = []
    for index, question in enumerate(questions, start=1):
        print(f"[{backend}] {index}/{len(questions)}: {question}", flush=True)
        try:
            started = time.perf_counter()
            vector = embed(question)
            embedded = time.perf_counter()
            top_chunk_id, top_similarity = query_chroma(collection, vector, top_k)
            finished = time.perf_counter()
            rows.append(
                Measurement(
                    question_index=index,
                    question=question,
                    backend=backend,
                    embedding_model=model_name,
                    embedding_seconds=embedded - started,
                    chroma_query_seconds=finished - embedded,
                    total_retrieval_seconds=finished - started,
                    top_chunk_id=top_chunk_id,
                    top_similarity=top_similarity,
                )
            )
        except Exception as exc:
            failure_wait = time.perf_counter() - started
            rows.append(
                Measurement(
                    question_index=index,
                    question=question,
                    backend=backend,
                    embedding_model=model_name,
                    embedding_seconds=None,
                    chroma_query_seconds=None,
                    total_retrieval_seconds=None,
                    top_chunk_id=None,
                    top_similarity=None,
                    error=f"{type(exc).__name__}: {exc}",
                    failure_wait_seconds=failure_wait,
                )
            )
    return rows


def seconds(value: float | None) -> str:
    return "ERROR" if value is None else f"{value:.3f}"


def timing_cell(row: dict, field: str) -> str:
    value = row.get(field)
    if value is not None:
        return seconds(value)
    waited = row.get("failure_wait_seconds")
    return f"TIMEOUT ({waited:.1f}s)" if waited is not None else "N/A"


def markdown_report(payload: dict) -> str:
    local_rows = {row["question_index"]: row for row in payload["runs"].get("local", [])}
    api_rows = {row["question_index"]: row for row in payload["runs"].get("openrouter", [])}
    embedding_model = payload.get("embedding_model") or next(
        (
            row.get("embedding_model")
            for rows in payload["runs"].values()
            for row in rows
            if row.get("embedding_model")
        ),
        "N/A",
    )
    lines = [
        "# Benchmark embedding — multilingual-e5-large",
        "",
        f"Ngày chạy: {payload['generated_at']} · Top-k: {payload['top_k']}",
        "",
        "Phạm vi: đo query embedding và Chroma retrieval; **không** đo thời gian sinh câu trả lời của chat LLM.",
        "",
        "## Tổng hợp",
        "",
        "| Backend | Model embedding | Model load (s) | Embedding mean thành công (s) | Median (s) | P95 (s) | Mean attempt gồm lỗi (s) | Total retrieval mean (s) | Thành công |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for backend in ("local", "openrouter"):
        if backend not in payload["summary"]:
            continue
        summary = payload["summary"][backend]
        load = payload["model_load_seconds"].get(backend)
        lines.append(
            f"| {backend} | `{embedding_model}` | "
            f"{seconds(load) if load is not None else 'N/A'} | "
            f"{seconds(summary['embedding_mean_seconds'])} | "
            f"{seconds(summary['embedding_median_seconds'])} | "
            f"{seconds(summary['embedding_p95_seconds'])} | "
            f"{seconds(summary['attempt_mean_seconds'])} | "
            f"{seconds(summary['total_retrieval_mean_seconds'])} | "
            f"{summary['successful']}/{summary['questions']} |"
        )

    lines += [
        "",
        "## Chi tiết 10 câu hỏi",
        "",
        "| # | Câu hỏi | Local embedding (s) | OpenRouter embedding (s) | Local total (s) | OpenRouter total (s) | Top chunk trùng? |",
        "|---:|---|---:|---:|---:|---:|:---:|",
    ]
    for index, question in enumerate(payload["questions"], start=1):
        local = local_rows.get(index, {})
        api = api_rows.get(index, {})
        same_top = (
            "✓"
            if local.get("top_chunk_id") and local.get("top_chunk_id") == api.get("top_chunk_id")
            else "—"
        )
        lines.append(
            f"| {index} | {question.replace('|', '/')} | "
            f"{timing_cell(local, 'embedding_seconds')} | "
            f"{timing_cell(api, 'embedding_seconds')} | "
            f"{timing_cell(local, 'total_retrieval_seconds')} | "
            f"{timing_cell(api, 'total_retrieval_seconds')} | {same_top} |"
        )

    local_summary = payload["summary"].get("local")
    api_summary = payload["summary"].get("openrouter")
    lines += ["", "## Kết luận nhanh", ""]
    if local_summary:
        lines.append(
            f"- Local: {local_summary['successful']}/{local_summary['questions']} thành công; "
            f"embedding trung bình {seconds(local_summary['embedding_mean_seconds'])} giây/câu sau warmup."
        )
    if api_summary:
        lines.append(
            f"- OpenRouter: {api_summary['successful']}/{api_summary['questions']} thành công; "
            f"{api_summary['failed']} lỗi/timeout."
        )
    if (
        local_summary
        and api_summary
        and local_summary["embedding_mean_seconds"]
        and api_summary["embedding_mean_seconds"]
    ):
        speedup = api_summary["embedding_mean_seconds"] / local_summary["embedding_mean_seconds"]
        lines.append(
            f"- Trên request OpenRouter thành công, local nhanh hơn khoảng **{speedup:.1f}×** ở bước embedding."
        )

    lines += [
        "",
        "## Ghi chú đo",
        "",
        "- `model_load`: chi phí nạp weights local một lần khi app khởi động; không cộng vào từng query.",
        "- `embedding`: chỉ thời gian biến một câu hỏi thành vector 1.024 chiều.",
        "- `Chroma query`: chỉ thời gian tìm top-k bằng vector đã có.",
        "- `total retrieval`: embedding + Chroma query; chưa gồm chat LLM.",
        "- OpenRouter dùng cùng model `intfloat/multilingual-e5-large`; chênh lệch chủ yếu là network/provider.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="So sánh query embedding local và OpenRouter")
    parser.add_argument("--backend", choices=["local", "openrouter", "both"], default="both")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--api-timeout", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    embedding.load_env_file(DEFAULT_ENV_FILE)
    config = embedding.load_config(
        DEFAULT_ENV_FILE,
        require_api_key=args.backend in {"openrouter", "both"},
    )
    chroma_dir = embedding.resolve_project_path(
        os.getenv("CHROMA_DIR", ""), DEFAULT_CHROMA_DIR
    )
    collection = open_existing_collection(
        chroma_dir=chroma_dir,
        collection_name=os.getenv("CHROMA_COLLECTION", "").strip() or config.collection_name,
        expected_model=config.model,
    )

    runs: dict[str, list[Measurement]] = {}
    model_load_seconds: dict[str, float | None] = {}

    if args.backend in {"local", "both"}:
        started = time.perf_counter()
        warmup_local_model()
        model_load_seconds["local"] = time.perf_counter() - started
        runs["local"] = run_backend(
            "local",
            config.model,
            QUESTIONS,
            embed_query,
            collection,
            args.top_k,
        )

    if args.backend in {"openrouter", "both"}:
        model_load_seconds["openrouter"] = None
        api_config = replace(
            config,
            document_prefix=os.getenv("EMBEDDING_QUERY_PREFIX", "query:").strip(),
            timeout_seconds=args.api_timeout,
            max_retries=1,
        )
        with requests.Session() as session:
            runs["openrouter"] = run_backend(
                "openrouter",
                config.model,
                QUESTIONS,
                lambda question: embedding.request_embeddings([question], api_config, session)[0],
                collection,
                args.top_k,
            )

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "embedding_model": config.model,
        "local_model_path": str(resolve_model_path()),
        "top_k": args.top_k,
        "questions": QUESTIONS,
        "model_load_seconds": model_load_seconds,
        "summary": {backend: summarize(rows) for backend, rows in runs.items()},
        "runs": {backend: [asdict(row) for row in rows] for backend, rows in runs.items()},
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "embedding-benchmark.json"
    markdown_path = args.output_dir / "embedding-benchmark.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(payload), encoding="utf-8")
    print(f"JSON: {json_path.resolve()}")
    print(f"Markdown: {markdown_path.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Lỗi benchmark: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
