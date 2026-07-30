"""Test gọi model thật — mặc định bị loại bởi `addopts = -m 'not live'`.

Chạy: `uv run pytest -m live`
"""

import os

import pytest

from src.chatbot.chatbot import Chatbot
from src.chatbot.config import Settings
from src.chatbot.types import Chunk, ToolRegistry

from fakes import FakeRetriever, make_fake_search_tool
from src.chatbot.react import ReActAgent

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.getenv("OPENAI_API"), reason="thiếu OPENAI_API trong .env"),
]

# Dữ kiện bịa — model không thể biết nếu không đọc tài liệu.
SECRET = Chunk("Ma xac minh cua nhom K3 la ZX-7741, doc tai buoi demo.", "noi-bo.md")


@pytest.fixture
def live_agent() -> ReActAgent:
    retriever = FakeRetriever([SECRET])
    registry = ToolRegistry([make_fake_search_tool(retriever)])
    bot = Chatbot(settings=Settings.from_env(), retriever=retriever)
    return ReActAgent(registry, chatbot=bot, max_steps=4)


def test_agent_lay_duoc_du_kien_chi_co_trong_tai_lieu(live_agent: ReActAgent):
    res = live_agent.run("Ma xac minh cua nhom K3 la gi?")
    assert "ZX-7741" in res.answer
    assert res.stopped_early is False


def test_khong_bia_khi_ngoai_pham_vi_tai_lieu(live_agent: ReActAgent):
    res = live_agent.run("Thu do cua nuoc Phap la gi?")
    assert "paris" not in res.answer.lower()
    assert "không có trong tài liệu" in res.answer.lower()
