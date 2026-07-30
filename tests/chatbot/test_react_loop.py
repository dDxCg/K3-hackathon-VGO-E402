"""Vòng phản hồi ReAct — mọi nhánh, chạy trên phản hồi kịch bản hoá."""

from src.chatbot.chatbot import Chatbot
from src.chatbot.types import ToolRegistry
from src.chatbot.react import ReActAgent

ACT = 'Thought: can tra tai lieu\nAction: search_docs\nAction Input: {"query": "CP3"}'
FINAL = "Thought: du du kien\nFinal Answer: CP3 luc 16:00 ngay 1."


def agent(
    registry: ToolRegistry, bot: Chatbot, max_steps: int = 4, prefetch_rag: bool = False
) -> ReActAgent:
    return ReActAgent(registry, chatbot=bot, max_steps=max_steps, prefetch_rag=prefetch_rag)


def test_final_answer_ngay_lap_tuc(registry, bare_bot, script):
    script(bare_bot, FINAL)
    res = agent(registry, bare_bot).run("CP3 luc nao?")
    assert res.answer == "CP3 luc 16:00 ngay 1."
    assert len(res.steps) == 1
    assert res.steps[0].observation == "<final>"
    assert res.steps[0].thought == "du du kien"
    assert res.stopped_early is False


def test_goi_tool_roi_chot(registry, bare_bot, script):
    script(bare_bot, ACT, FINAL)
    res = agent(registry, bare_bot).run("CP3 luc nao?")
    assert len(res.steps) == 2
    assert res.steps[0].action == "search_docs"
    assert res.steps[0].action_input == {"query": "CP3"}
    assert "[rubric.md]" in res.steps[0].observation
    assert res.answer == "CP3 luc 16:00 ngay 1."


def test_registry_nhan_dung_ten_tool_dang_goi_ham(registry, bare_bot, script):
    """Hồi quy: `Action: search_docs("CP3")` từng làm registry báo không có tool."""
    raw = 'Thought: t\nAction: search_docs("CP3")\nAction Input: {"query": "CP3"}'
    script(bare_bot, raw, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert res.steps[0].action == "search_docs"
    assert "Lỗi" not in res.steps[0].observation


def test_feedback_sai_tham_so_roi_thu_lai(registry, bare_bot, script):
    bad = 'Thought: t\nAction: search_docs\nAction Input: {"tham_so": "CP3"}'
    script(bare_bot, bad, ACT, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert "Lỗi khi chạy 'search_docs'" in res.steps[0].observation
    assert "TypeError" in res.steps[0].observation
    assert "[rubric.md]" in res.steps[1].observation
    assert res.stopped_early is False


def test_feedback_tool_khong_ton_tai(registry, bare_bot, script):
    bad = 'Thought: t\nAction: khong_ton_tai\nAction Input: {"x": 1}'
    script(bare_bot, bad, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert "không có tool tên 'khong_ton_tai'" in res.steps[0].observation
    assert len(res.steps) == 2  # vòng lặp chạy tiếp chứ không chết


def test_action_input_hong_khong_lam_vo_vong_lap(registry, bare_bot, script):
    bad = "Thought: t\nAction: search_docs\nAction Input: {query: CP3"
    script(bare_bot, bad, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert res.steps[0].observation.startswith("Lỗi: ")
    assert "JSON" in res.steps[0].observation
    assert res.answer == "CP3 luc 16:00 ngay 1."


def test_repeat_guard_canh_bao_khi_goi_trung(registry, bare_bot, script):
    script(bare_bot, ACT, ACT, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert "[Cảnh báo]" not in res.steps[0].observation
    assert "[Cảnh báo]" in res.steps[1].observation


def test_doi_tham_so_thi_khong_canh_bao(registry, bare_bot, script):
    other = 'Thought: t\nAction: search_docs\nAction Input: {"query": "Demo"}'
    script(bare_bot, ACT, other, FINAL)
    res = agent(registry, bare_bot).run("CP3?")
    assert all("[Cảnh báo]" not in s.observation for s in res.steps)


def test_het_max_steps_thi_ep_chot(registry, bare_bot, script):
    llm = script(bare_bot, ACT, ACT, "Final Answer: chot tam.")
    res = agent(registry, bare_bot, max_steps=2).run("CP3?")
    assert res.stopped_early is True
    assert len(res.steps) == 2
    assert res.answer == "chot tam."
    assert len(llm.calls) == 3  # 2 vòng + 1 lần ép chốt
    assert "Hết số bước cho phép" in llm.last_messages[-1]["content"]


def test_khong_action_khong_final_thi_lay_ca_output(registry, bare_bot, script):
    script(bare_bot, "Thought: minh tra loi thang vay.")
    res = agent(registry, bare_bot).run("CP3?")
    assert len(res.steps) == 1
    assert res.answer == "Thought: minh tra loi thang vay."
    assert res.stopped_early is False


def test_prefill_thought_va_stop_sequence(registry, bare_bot, script):
    llm = script(bare_bot, "Final Answer: xong.")
    res = agent(registry, bare_bot).run("CP3?")
    assert res.steps[0].raw.startswith("Thought:")  # được mồi khi model bỏ nhãn
    assert llm.calls[0][-1]["role"] == "assistant"
    assert llm.calls[0][-1]["content"].endswith("Thought:")
    assert llm.stops[0] == ["Observation:", "\nObservation:"]


def test_scratchpad_tich_luy_observation(registry, bare_bot, script):
    llm = script(bare_bot, ACT, FINAL)
    agent(registry, bare_bot).run("CP3?")
    prefill = llm.calls[1][-1]["content"]
    assert "Observation:" in prefill
    assert "[rubric.md]" in prefill
    assert prefill.endswith("Thought:")


def test_prefetch_mac_dinh_la_tat(registry, bot):
    assert ReActAgent(registry, chatbot=bot).prefetch_rag is False


def test_mac_dinh_khong_pre_retrieve(registry, bot, script):
    """Agent có search_docs thì không đổ sẵn chunk vào prompt — tránh embed 2 lần."""
    llm = script(bot, FINAL)
    agent(registry, bot).run("CP3 luc 16:00 ngay 1")
    system = llm.calls[0][0]
    assert system["role"] == "system"
    assert "## Ngữ cảnh truy xuất" not in system["content"]
    assert bot.last_retrieved == []  # retriever chưa hề bị gọi


def test_bat_prefetch_thi_do_chunk_vao_prompt(registry, bot, script):
    """Bật lại cho trường hợp registry không có tool tìm kiếm."""
    llm = script(bot, FINAL)
    res = agent(registry, bot, prefetch_rag=True).run("CP3 luc 16:00 ngay 1")
    assert res.retrieved and res.retrieved[0].source == "rubric.md"
    assert "Ngữ cảnh truy xuất" in llm.calls[0][0]["content"]


def test_khong_co_rag_thi_retrieved_rong(registry, bare_bot, script):
    script(bare_bot, FINAL)
    assert agent(registry, bare_bot, prefetch_rag=True).run("CP3?").retrieved == []


def test_tool_signature_tu_registry_vao_prompt(registry, bare_bot, script):
    llm = script(bare_bot, FINAL)
    agent(registry, bare_bot).run("CP3?")
    system = llm.calls[0][0]["content"]
    assert "search_docs(query: str, k: int = 5) -> str" in system
    assert "Giao thức ReAct" in system


def test_history_giu_qua_hai_luot_va_reset(registry, bare_bot, script):
    llm = script(bare_bot, FINAL, "Final Answer: luot hai.")
    ag = agent(registry, bare_bot)
    ag.run("cau 1")
    ag.run("cau 2")
    roles = [m["role"] for m in llm.calls[1]]
    assert roles[:4] == ["system", "user", "assistant", "user"]
    assert llm.calls[1][1]["content"] == "cau 1"
    assert llm.calls[1][2]["content"] == "CP3 luc 16:00 ngay 1."
    ag.reset()
    assert ag.bot.history == []
