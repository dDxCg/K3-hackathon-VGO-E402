"""Render system prompt — các khối điều kiện trong system.j2."""

from src.chatbot.mock.rag import Chunk
from src.chatbot.prompt import ToolSignature, render_system_prompt

TOOL = ToolSignature(
    name="search_docs",
    description="Tìm đoạn tài liệu khoá học liên quan tới truy vấn.",
    signature="search_docs(query: str, k: int = 5) -> str",
)


def test_khong_tool_thi_bao_chua_co():
    out = render_system_prompt()
    assert "Chưa có tool nào" in out
    assert "search_docs" not in out


def test_tool_signature_do_vao_prompt():
    out = render_system_prompt(tool_signatures=[TOOL])
    assert TOOL.name in out
    assert TOOL.description in out
    assert TOOL.signature in out
    assert "Chưa có tool nào" not in out


def test_khoi_react_tat_mac_dinh():
    assert "Giao thức ReAct" not in render_system_prompt(tool_signatures=[TOOL])


def test_khoi_react_bat_kem_max_steps():
    out = render_system_prompt(tool_signatures=[TOOL], react=True, max_steps=3)
    assert "Giao thức ReAct" in out
    assert "tối đa 3 bước" in out
    assert "Final Answer" in out


def test_khong_co_chunk_thi_bo_muc_ngu_canh():
    out = render_system_prompt(tool_signatures=[TOOL])
    assert "Ngữ cảnh truy xuất" not in out


def test_chunk_rag_do_vao_prompt_kem_source_va_score():
    chunks = [Chunk("CP3 luc 16:00 ngay 1.", "rubric.md", score=0.5)]
    out = render_system_prompt(retrieved=chunks)
    assert "Ngữ cảnh truy xuất" in out
    assert "[rubric.md]" in out
    assert "CP3 luc 16:00 ngay 1." in out
    assert "score=0.500" in out
    assert "Trích nguồn" in out  # nguyên tắc trích nguồn chỉ bật khi có chunk


def test_score_bang_khong_thi_khong_in_score():
    out = render_system_prompt(retrieved=[Chunk("x", "a.md", score=0.0)])
    assert "score=" not in out


def test_context_bo_sung():
    assert "Ngữ cảnh bổ sung" not in render_system_prompt()
    out = render_system_prompt(context="Người học đang ở CP2.")
    assert "Ngữ cảnh bổ sung" in out
    assert "Người học đang ở CP2." in out


def test_render_du_bien_khong_ne_undefined():
    """StrictUndefined: thiếu biến sẽ ném UndefinedError — bản đầy đủ phải sạch."""
    out = render_system_prompt(
        tool_signatures=[TOOL],
        retrieved=[Chunk("x", "a.md", score=0.1)],
        context="ctx",
        react=True,
        max_steps=6,
    )
    assert out.strip()
