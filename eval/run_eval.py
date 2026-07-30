"""Chạy bộ eval 20 câu qua stack thật và chấm theo checks trong questions.json.

    uv run python eval/run_eval.py                  # chạy hết
    uv run python eval/run_eval.py --ids S01 M04    # chạy vài case
    uv run python eval/run_eval.py --type multi     # lọc theo loại

Kết quả ghi vào eval/results.json. Cột quan trọng nhất là `status`:
- as_expected  : khớp trạng thái đã biết (pass đúng như kỳ vọng, hoặc fail đúng lỗi đã ghi)
- regression   : case đang xanh nay đỏ  -> hỏng thứ vốn chạy được
- improvement  : case đang đỏ nay xanh  -> lỗi đã được sửa, cập nhật lại `expect`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.chatbot.admission_agent import build_admission_agent  # noqa: E402


def check_case(checks: dict, answer: str, tools: list[str], steps: int, stopped_early: bool) -> list[str]:
    """Trả về danh sách lý do trượt; rỗng nghĩa là đạt."""
    failures: list[str] = []
    haystack = answer.casefold()

    for tool in checks.get("tools_all", []):
        if tool not in tools:
            failures.append(f"thiếu tool `{tool}` (đã gọi: {tools or 'không tool nào'})")

    any_tools = checks.get("tools_any", [])
    if any_tools and not any(tool in tools for tool in any_tools):
        failures.append(f"không gọi tool nào trong {any_tools}")

    for tool in checks.get("tools_forbidden", []):
        if tool in tools:
            failures.append(f"gọi tool bị cấm `{tool}`")

    for needle in checks.get("answer_all", []):
        if needle.casefold() not in haystack:
            failures.append(f"đáp án thiếu '{needle}'")

    any_answers = checks.get("answer_any", [])
    if any_answers and not any(n.casefold() in haystack for n in any_answers):
        failures.append(f"đáp án không chứa chuỗi nào trong {any_answers}")

    for needle in checks.get("answer_none", []):
        if needle.casefold() in haystack:
            failures.append(f"đáp án chứa chuỗi cấm '{needle}'")

    min_steps = checks.get("min_steps")
    if min_steps is not None and steps < min_steps:
        failures.append(f"chỉ {steps} bước, cần ≥ {min_steps}")

    if checks.get("not_stopped_early") and stopped_early:
        failures.append("chạm trần max_steps")

    return failures


def run_case(case: dict, max_steps: int) -> dict:
    agent = build_admission_agent(max_steps=max_steps)
    started = time.perf_counter()
    try:
        result = agent.run(case["question"])
    except Exception as exc:  # lỗi hạ tầng không được làm chết cả bộ eval
        return {
            **{k: case[k] for k in ("id", "type", "category", "question", "expect")},
            "error": f"{type(exc).__name__}: {exc}",
            "passed": False,
            "status": "error",
            "failures": ["exception khi chạy"],
            "seconds": round(time.perf_counter() - started, 2),
        }
    elapsed = time.perf_counter() - started

    tools = [step.action for step in result.steps if step.action]
    failures = check_case(
        case.get("checks", {}),
        result.answer,
        tools,
        len(result.steps),
        result.stopped_early,
    )
    passed = not failures
    expect_pass = case["expect"] == "pass"
    if passed == expect_pass:
        status = "as_expected"
    else:
        status = "improvement" if passed else "regression"

    return {
        **{k: case[k] for k in ("id", "type", "category", "question", "expect")},
        "why": case.get("why", ""),
        "passed": passed,
        "status": status,
        "failures": failures,
        "tools": tools,
        "steps": len(result.steps),
        "stopped_early": result.stopped_early,
        "best_score": round(result.retrieved[0].score, 4) if result.retrieved else None,
        "retrieved_sources": [c.metadata.get("source_type") for c in result.retrieved],
        "answer": result.answer,
        "seconds": round(elapsed, 2),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="run_eval")
    parser.add_argument("--ids", nargs="*", help="chỉ chạy các case id này")
    parser.add_argument("--type", choices=["single", "multi"], help="lọc theo loại câu hỏi")
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results.json")
    args = parser.parse_args()

    suite = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))
    cases = suite["cases"]
    if args.ids:
        cases = [c for c in cases if c["id"] in set(args.ids)]
    if args.type:
        cases = [c for c in cases if c["type"] == args.type]

    results = []
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case['id']} … ", end="", flush=True)
        record = run_case(case, args.max_steps)
        results.append(record)
        mark = "PASS" if record["passed"] else "FAIL"
        print(f"{mark} ({record['status']}, {record['seconds']}s)")
        if record["failures"]:
            for reason in record["failures"]:
                print(f"        - {reason}")

    passed = sum(r["passed"] for r in results)
    by_status: dict[str, int] = {}
    for record in results:
        by_status[record["status"]] = by_status.get(record["status"], 0) + 1

    summary = {
        "version": suite["version"],
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "by_status": by_status,
        "total_seconds": round(sum(r["seconds"] for r in results), 1),
        "results": results,
    }
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{passed}/{len(results)} đạt · {by_status} · {summary['total_seconds']}s")
    print(f"Chi tiết: {args.out}")
    regressions = [r["id"] for r in results if r["status"] == "regression"]
    if regressions:
        print(f"REGRESSION: {regressions}")


if __name__ == "__main__":
    main()
