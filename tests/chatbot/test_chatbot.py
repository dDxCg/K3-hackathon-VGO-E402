"""Chatbot — history, retrieve, messages, stream."""

from types import SimpleNamespace

from src.chatbot.chatbot import Chatbot
from src.chatbot.mock.rag import NullRetriever


def test_chat_ghi_history(bot: Chatbot, script):
    script(bot, "tra loi 1", "tra loi 2")
    assert bot.chat("cau 1") == "tra loi 1"
    bot.chat("cau 2")
    assert [m["content"] for m in bot.history] == [
        "cau 1",
        "tra loi 1",
        "cau 2",
        "tra loi 2",
    ]
    assert [m["role"] for m in bot.history] == ["user", "assistant"] * 2


def test_messages_dung_thu_tu(bot: Chatbot, script):
    llm = script(bot, "a", "b")
    bot.chat("cau 1")
    bot.chat("cau 2")
    roles = [m["role"] for m in llm.calls[1]]
    assert roles == ["system", "user", "assistant", "user"]
    assert llm.calls[1][-1]["content"] == "cau 2"


def test_retrieve_set_last_retrieved_va_top_k(settings, retriever):
    bot = Chatbot(settings=settings, retriever=retriever, top_k=1)
    got = bot.retrieve("CP3 ngay 1")
    assert len(got) == 1
    assert bot.last_retrieved == got


def test_reset_xoa_history_va_retrieved(bot: Chatbot, script):
    script(bot, "x")
    bot.chat("CP3 ngay 1")
    assert bot.history and bot.last_retrieved
    bot.reset()
    assert bot.history == []
    assert bot.last_retrieved == []


def test_system_prompt_khong_rag_thi_bo_muc_ngu_canh(settings):
    bot = Chatbot(settings=settings, retriever=NullRetriever())
    assert "Ngữ cảnh truy xuất" not in bot.system_prompt("bat ky")


def test_system_prompt_react_flag(bot: Chatbot):
    assert "Giao thức ReAct" not in bot.system_prompt("x")
    assert "Giao thức ReAct" in bot.system_prompt("x", react=True, max_steps=3)


def test_stream_yield_token_va_gop_vao_history(bot: Chatbot):
    def fake_create(**kwargs):
        assert kwargs["stream"] is True
        for token in ["CP3 ", "luc ", "16:00"]:
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=token))]
            )
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))])

    bot.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    assert list(bot.stream("CP3?")) == ["CP3 ", "luc ", "16:00"]
    assert bot.history[-1] == {"role": "assistant", "content": "CP3 luc 16:00"}
