"""Test cho eval/judge.py — chạy hoàn toàn offline, judge được tiêm bằng hàm giả.

Không case nào gọi mạng: `Judge` nhận `complete` từ ngoài, nên toàn bộ logic tách
claim / tính điểm / cache đều kiểm được mà không tốn token.
"""

import json
import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(EVAL_DIR))

from judge import (  # noqa: E402
    Judge,
    JudgeSample,
    JudgeSettings,
    mean_ignoring_none,
    parse_json,
)


SAMPLE = JudgeSample(
    id="S02",
    question="Mỗi khoá tuyển tối đa bao nhiêu học viên?",
    answer="Chỉ tiêu là tối đa 500 học viên mỗi khoá.",
    contexts=["Chỉ tiêu tuyển sinh: tối đa 500 học viên/ khoá"],
    reference="Chỉ tiêu tuyển sinh là tối đa 500 học viên mỗi khoá.",
)


class ScriptedJudge:
    """Trả lần lượt các output đã kịch bản hoá; đếm số lượt gọi."""

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    def __call__(self, messages):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("ScriptedJudge hết output — judge gọi nhiều hơn dự kiến")
        return self.responses.pop(0)


def claims(*items: str) -> str:
    return json.dumps({"claims": list(items)}, ensure_ascii=False)


def verdicts(*supported: bool) -> str:
    return json.dumps(
        {"verdicts": [{"supported": s, "reason": "r"} for s in supported]}, ensure_ascii=False
    )


def score(value, **extra) -> str:
    return json.dumps({"score": value, "reason": "r", **extra}, ensure_ascii=False)


# --- parse ---------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        '{"score": 0.5}',
        '```json\n{"score": 0.5}\n```',
        'Đây là kết quả:\n{"score": 0.5}\nHết.',
    ],
)
def test_parse_json_boc_duoc_moi_bien_the(raw):
    assert parse_json(raw)["score"] == 0.5


def test_parse_json_khong_co_object_thi_bao_loi():
    with pytest.raises(ValueError):
        parse_json("không có json ở đây")


def test_parse_json_mang_khong_phai_object():
    with pytest.raises(ValueError):
        parse_json("[1, 2, 3]")


# --- faithfulness --------------------------------------------------------


def test_faithfulness_la_ti_le_claim_duoc_ho_tro():
    judge = Judge(complete=ScriptedJudge(claims("a", "b", "c", "d"), verdicts(True, True, True, False)),
                  cache_path=None)
    result = judge.faithfulness(SAMPLE)
    assert result.score == 0.75
    assert result.detail["supported"] == 3
    assert result.detail["total"] == 4


def test_faithfulness_chi_ra_dung_claim_khong_co_can_cu():
    judge = Judge(complete=ScriptedJudge(claims("đúng", "bịa"), verdicts(True, False)), cache_path=None)
    detail = judge.faithfulness(SAMPLE).detail["claims"]
    assert [c["claim"] for c in detail if not c["supported"]] == ["bịa"]


def test_khong_tach_duoc_claim_thi_None_chu_khong_phai_0():
    """Answer chỉ có lời mời liên hệ — không đo được, khác hẳn 'đo được và bằng 0'."""
    judge = Judge(complete=ScriptedJudge(claims()), cache_path=None)
    result = judge.faithfulness(SAMPLE)
    assert result.score is None
    assert "claim" in result.error


def test_answer_rong_thi_khong_goi_judge():
    scripted = ScriptedJudge()
    judge = Judge(complete=scripted, cache_path=None)
    result = judge.faithfulness(JudgeSample("X", "q", "   ", ["ctx"]))
    assert result.score is None
    assert scripted.calls == []


def test_khong_co_context_thi_None():
    judge = Judge(complete=ScriptedJudge(), cache_path=None)
    assert judge.faithfulness(JudgeSample("X", "q", "a", [])).score is None


def test_lech_so_verdict_thi_None_chu_khong_tinh_bua():
    judge = Judge(complete=ScriptedJudge(claims("a", "b", "c"), verdicts(True)), cache_path=None)
    result = judge.faithfulness(SAMPLE)
    assert result.score is None
    assert "verdict" in result.error


# --- relevancy / correctness --------------------------------------------


def test_relevancy_lay_diem_va_ly_do():
    judge = Judge(complete=ScriptedJudge(score(0.8)), cache_path=None)
    result = judge.answer_relevancy(SAMPLE)
    assert result.score == 0.8
    assert result.detail["reason"] == "r"


def test_diem_thang_100_duoc_keo_ve_0_1():
    judge = Judge(complete=ScriptedJudge(score(80)), cache_path=None)
    assert judge.answer_relevancy(SAMPLE).score == 0.8


def test_diem_am_bi_ket_ve_0():
    judge = Judge(complete=ScriptedJudge(score(-3)), cache_path=None)
    assert judge.answer_relevancy(SAMPLE).score == 0.0


def test_correctness_giu_danh_sach_sai_va_thieu():
    judge = Judge(complete=ScriptedJudge(score(0.4, wrong=["30 tuần"], missing=["500"])), cache_path=None)
    detail = judge.answer_correctness(SAMPLE).detail
    assert detail["wrong"] == ["30 tuần"]
    assert detail["missing"] == ["500"]


def test_thieu_reference_thi_khong_cham_correctness():
    judge = Judge(complete=ScriptedJudge(), cache_path=None)
    result = judge.answer_correctness(JudgeSample("X", "q", "a", ["ctx"], reference=""))
    assert result.score is None
    assert "reference" in result.error


# --- chịu lỗi ------------------------------------------------------------


def test_json_hong_thi_thu_lai_mot_lan():
    judge = Judge(complete=ScriptedJudge("không phải json", score(0.6)), cache_path=None)
    assert judge.answer_relevancy(SAMPLE).score == 0.6


def test_json_hong_ca_hai_lan_thi_None_khong_crash():
    judge = Judge(complete=ScriptedJudge("hỏng", "vẫn hỏng"), cache_path=None)
    result = judge.answer_relevancy(SAMPLE)
    assert result.score is None
    assert result.error


# --- cache ---------------------------------------------------------------


def test_cache_hit_khong_goi_judge_lan_hai(tmp_path):
    cache = tmp_path / "judge_cache.json"
    scripted = ScriptedJudge(score(0.9))
    judge = Judge(complete=scripted, cache_path=cache)
    assert judge.answer_relevancy(SAMPLE).score == 0.9
    judge.save_cache()

    again = Judge(complete=ScriptedJudge(), cache_path=cache)  # hết output: gọi thêm là nổ
    result = again.answer_relevancy(SAMPLE)
    assert result.score == 0.9
    assert result.cached is True
    assert again.llm_calls == 0


def test_doi_prompt_version_thi_cache_miss(tmp_path):
    cache = tmp_path / "judge_cache.json"
    Judge(complete=ScriptedJudge(score(0.9)), cache_path=cache, prompt_version="1").answer_relevancy(SAMPLE)
    judge = Judge(complete=ScriptedJudge(score(0.9)), cache_path=cache, prompt_version="1")
    judge.answer_relevancy(SAMPLE)
    judge.save_cache()

    v2 = Judge(complete=ScriptedJudge(score(0.2)), cache_path=cache, prompt_version="2")
    assert v2.answer_relevancy(SAMPLE).score == 0.2
    assert v2.llm_calls == 1


def test_doi_answer_thi_cache_miss(tmp_path):
    cache = tmp_path / "judge_cache.json"
    judge = Judge(complete=ScriptedJudge(score(0.9)), cache_path=cache)
    judge.answer_relevancy(SAMPLE)
    judge.save_cache()

    other = Judge(complete=ScriptedJudge(score(0.1)), cache_path=cache)
    changed = JudgeSample(SAMPLE.id, SAMPLE.question, "câu khác hẳn", SAMPLE.contexts, SAMPLE.reference)
    assert other.answer_relevancy(changed).score == 0.1


# --- settings ------------------------------------------------------------


def test_judge_model_trung_model_san_pham_thi_raise(monkeypatch):
    """Model tự chấm bài mình viết là self-preference bias."""
    monkeypatch.setenv("OPENAI_API", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("JUDGE_MODEL", "openai/gpt-4o-mini")
    with pytest.raises(RuntimeError, match="self-preference"):
        JudgeSettings.from_env()


def test_judge_model_khac_thi_chay(monkeypatch):
    monkeypatch.setenv("OPENAI_API", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("JUDGE_MODEL", "google/gemini-2.5-flash")
    assert JudgeSettings.from_env().model == "google/gemini-2.5-flash"


def test_thieu_api_key_thi_raise(monkeypatch):
    monkeypatch.delenv("OPENAI_API", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API"):
        JudgeSettings.from_env()


# --- tổng hợp ------------------------------------------------------------


def test_trung_binh_bo_qua_None():
    assert mean_ignoring_none([1.0, None, 0.0]) == 0.5


def test_toan_None_thi_tra_None():
    assert mean_ignoring_none([None, None]) is None
