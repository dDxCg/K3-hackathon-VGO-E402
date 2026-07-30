from eval.benchmark_embedding import Measurement, markdown_report, percentile, summarize


def row(index, embedding_seconds, total_seconds):
    return Measurement(
        question_index=index,
        question=f"q{index}",
        backend="local",
        embedding_model="model",
        embedding_seconds=embedding_seconds,
        chroma_query_seconds=0.01 if embedding_seconds is not None else None,
        total_retrieval_seconds=total_seconds,
        top_chunk_id=f"chunk_{index}" if embedding_seconds is not None else None,
        top_similarity=0.8 if embedding_seconds is not None else None,
        error=None if embedding_seconds is not None else "timeout",
        failure_wait_seconds=None if embedding_seconds is not None else 60.0,
    )


def test_percentile_nearest_rank():
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5
    assert percentile([], 0.95) == 0.0


def test_summarize_excludes_failed_rows():
    summary = summarize([row(1, 0.1, 0.11), row(2, 0.3, 0.31), row(3, None, None)])
    assert summary["questions"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert summary["embedding_mean_seconds"] == 0.2
    assert summary["attempt_mean_seconds"] == (0.1 + 0.3 + 60.0) / 3


def test_markdown_report_labels_embedding_time_separately():
    measurement = row(1, 0.1, 0.11)
    payload = {
        "generated_at": "2026-07-30T00:00:00+07:00",
        "top_k": 5,
        "questions": ["q1"],
        "model_load_seconds": {"local": 10.0},
        "summary": {"local": summarize([measurement])},
        "runs": {"local": [measurement.__dict__]},
    }
    report = markdown_report(payload)
    assert "Local embedding (s)" in report
    assert "model_load" in report
    assert "chat LLM" in report
