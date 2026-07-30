"""Chatbot cơ bản — OpenRouter qua OpenAI SDK."""

from collections.abc import Iterator, Sequence
from typing import Any

from openai import OpenAI

from .config import Settings
from .mock.rag import Chunk, NullRetriever, Retriever
from .prompt import ToolSignature, render_system_prompt


class Chatbot:
    def __init__(
        self,
        settings: Settings | None = None,
        tool_signatures: Sequence[Any] | None = None,
        retriever: Retriever | None = None,
        context: str = "",
        top_k: int = 5,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.tool_signatures: list[Any] = list(tool_signatures or [])
        self.retriever: Retriever = retriever or NullRetriever()
        self.context = context
        self.top_k = top_k
        self.client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )
        self.history: list[dict[str, str]] = []
        self.last_retrieved: list[Chunk] = []

    def retrieve(self, query: str) -> list[Chunk]:
        self.last_retrieved = self.retriever.retrieve(query, k=self.top_k)
        return self.last_retrieved

    def system_prompt(self, query: str, react: bool = False, max_steps: int = 6) -> str:
        return render_system_prompt(
            tool_signatures=self.tool_signatures,
            retrieved=self.retrieve(query),
            context=self.context,
            react=react,
            max_steps=max_steps,
        )

    def _messages(self, user_message: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt(user_message)},
            *self.history,
            {"role": "user", "content": user_message},
        ]

    def complete(
        self,
        messages: list[dict[str, str]],
        stop: list[str] | None = None,
    ) -> str:
        """Một lượt gọi model, không đụng history — ReAct agent dùng lại."""
        response = self.client.chat.completions.create(
            model=self.settings.model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            stop=stop,
        )
        return response.choices[0].message.content or ""

    def chat(self, user_message: str) -> str:
        reply = self.complete(self._messages(user_message))
        self._remember(user_message, reply)
        return reply

    def stream(self, user_message: str) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.settings.model,
            messages=self._messages(user_message),
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            stream=True,
        )
        chunks: list[str] = []
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                chunks.append(delta)
                yield delta
        self._remember(user_message, "".join(chunks))

    def _remember(self, user_message: str, reply: str) -> None:
        self.history += [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ]

    def reset(self) -> None:
        self.history.clear()
        self.last_retrieved = []


__all__ = ["Chatbot", "ToolSignature"]
