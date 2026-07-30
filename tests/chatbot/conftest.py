"""Fixture dùng chung — mọi test mặc định chạy offline.

`Chatbot.complete()` là điểm duy nhất chạm mạng, nên test thay nó bằng
`ScriptedLLM` để vòng ReAct trở nên xác định.
"""

import pytest

from src.chatbot.chatbot import Chatbot
from src.chatbot.config import Settings
from src.chatbot.types import Chunk, NullRetriever, ToolRegistry

from fakes import FakeRetriever, make_fake_search_tool


class ScriptedLLM:
    """Trả lần lượt từng phản hồi đã kịch bản hoá; ghi lại messages để assert."""

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict]] = []
        self.stops: list[list[str] | None] = []

    def __call__(self, messages, stop=None):
        self.calls.append(messages)
        self.stops.append(stop)
        if not self.responses:
            raise AssertionError("ScriptedLLM hết phản hồi — vòng lặp gọi nhiều hơn dự kiến")
        return self.responses.pop(0)

    @property
    def last_messages(self) -> list[dict]:
        return self.calls[-1]


@pytest.fixture
def settings() -> Settings:
    """Settings giả — không đọc .env, không gọi mạng."""
    return Settings(
        api_key="test-key",
        model="test/model",
        base_url="https://example.invalid/v1",
        temperature=0.0,
        max_tokens=256,
    )


@pytest.fixture
def docs() -> list[Chunk]:
    return [
        Chunk("CP3 luc 16:00 ngay 1, phai co AI chay that va do luot dau.", "rubric.md"),
        Chunk("Spec nop han cung 23:59 ngay 1, khong gia han.", "de-bai.md"),
        Chunk("Demo CP6 luc 10:00 ngay 2, moi nhom 5 phut.", "rubric.md"),
    ]


@pytest.fixture
def retriever(docs: list[Chunk]) -> FakeRetriever:
    return FakeRetriever(docs)


@pytest.fixture
def registry(retriever: FakeRetriever) -> ToolRegistry:
    return ToolRegistry([make_fake_search_tool(retriever)])


@pytest.fixture
def bot(settings: Settings, retriever: FakeRetriever) -> Chatbot:
    """Chatbot có RAG thật (in-memory), chưa gắn ScriptedLLM."""
    return Chatbot(settings=settings, retriever=retriever)


@pytest.fixture
def bare_bot(settings: Settings) -> Chatbot:
    """Chatbot không RAG — buộc agent phải gọi tool."""
    return Chatbot(settings=settings, retriever=NullRetriever())


@pytest.fixture
def script():
    """Gắn ScriptedLLM vào một Chatbot: `llm = script(bot, "resp1", "resp2")`."""

    def attach(chatbot: Chatbot, *responses: str) -> ScriptedLLM:
        llm = ScriptedLLM(*responses)
        chatbot.complete = llm  # type: ignore[method-assign]
        return llm

    return attach
