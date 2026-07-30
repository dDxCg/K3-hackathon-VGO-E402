"""Hạ tầng cho test end-to-end: chạy hết stack thật, ghi lại số liệu từng case.

Khác với `tests/chatbot/` (mọi thứ kịch bản hoá, offline), ở đây không mock gì:
ChromaDB thật, E5-large local thật, model chat thật. Vì vậy assert phải nhắm vào
**hành vi bắt buộc** (gọi đúng tool, không bịa, có trích nguồn) chứ không nhắm
vào từng chữ trong câu trả lời — model sinh khác nhau mỗi lượt.
"""

import json
import os
import time
from pathlib import Path

import pytest

RESULTS: list[dict] = []
REPORT_PATH = Path(os.getenv("E2E_REPORT", "e2e_results.json"))


@pytest.fixture(scope="session")
def agent_factory():
    """Mỗi case một agent mới — không để lịch sử case trước ảnh hưởng case sau."""
    from src.chatbot.admission_agent import build_admission_agent

    def make(max_steps: int = 6):
        return build_admission_agent(max_steps=max_steps)

    return make


@pytest.fixture
def run_case(agent_factory, request):
    """Chạy một câu hỏi qua stack thật và ghi số liệu để dựng báo cáo."""

    def run(question: str, max_steps: int = 6):
        agent = agent_factory(max_steps=max_steps)
        started = time.perf_counter()
        result = agent.run(question)
        elapsed = time.perf_counter() - started

        RESULTS.append(
            {
                "case": request.node.name,
                "question": question,
                "answer": result.answer,
                "tools": [step.action for step in result.steps if step.action],
                "steps": len(result.steps),
                "stopped_early": result.stopped_early,
                "retrieved": [
                    {
                        "id": chunk.metadata.get("chunk_id"),
                        "score": round(chunk.score, 4),
                        "source_type": chunk.metadata.get("source_type"),
                    }
                    for chunk in result.retrieved
                ],
                "best_score": round(result.retrieved[0].score, 4) if result.retrieved else None,
                "seconds": round(elapsed, 2),
            }
        )
        return result

    return run


def pytest_sessionfinish(session, exitstatus):
    if RESULTS:
        REPORT_PATH.write_text(
            json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n[e2e] đã ghi {len(RESULTS)} case vào {REPORT_PATH}")
