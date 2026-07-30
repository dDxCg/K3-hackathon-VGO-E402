"""Vòng phản hồi ReAct: Thought -> Action -> Observation -> ... -> Final Answer."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .chatbot import Chatbot
from .mock.rag import Chunk
from .mock.tools import ToolRegistry

_ACTION_RE = re.compile(
    r"Action\s*:\s*(?P<name>[^\n]+)\s*\n\s*Action Input\s*:\s*(?P<args>.+?)\s*(?=\nThought:|\nObservation:|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_FINAL_RE = re.compile(r"Final Answer\s*:\s*(?P<answer>.*)", re.DOTALL | re.IGNORECASE)
_THOUGHT_RE = re.compile(r"Thought\s*:\s*(?P<thought>[^\n]*)", re.IGNORECASE)


@dataclass
class Step:
    """Một vòng lặp ReAct — dùng để trace/đo lường."""

    thought: str = ""
    action: str = ""
    action_input: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    raw: str = ""


@dataclass
class ReActResult:
    answer: str
    steps: list[Step]
    stopped_early: bool = False
    retrieved: list[Chunk] = field(default_factory=list)
    """Chunk RAG pre-retrieve, đã nằm sẵn trong system prompt trước bước ReAct đầu tiên."""


def _tool_name(raw: str) -> str:
    """Model hay viết `Action: search_docs("x")`, bọc backtick hoặc bôi đậm — lấy đúng tên tool."""
    name = raw.strip().strip("`\"'*").split("(", 1)[0]
    return name.strip().strip("`\"'*")


def _parse_args(raw: str) -> dict[str, Any]:
    """Model hay bọc JSON trong ```; gỡ ra rồi parse."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        args = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Action Input không phải JSON hợp lệ: {exc.msg}") from exc
    if not isinstance(args, dict):
        raise ValueError("Action Input phải là JSON object.")
    return args


class ReActAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        chatbot: Chatbot | None = None,
        max_steps: int = 6,
    ) -> None:
        self.registry = registry
        self.bot = chatbot or Chatbot()
        self.bot.tool_signatures = registry.signatures()
        self.max_steps = max_steps

    def run(self, question: str) -> ReActResult:
        # RAG chạy trước vòng lặp: chunk đổ thẳng vào system prompt.
        # Tool search_docs chỉ để agent tự truy vấn thêm khi ngữ cảnh này chưa đủ.
        system = self.bot.system_prompt(question, react=True, max_steps=self.max_steps)
        retrieved = list(self.bot.last_retrieved)
        scratchpad = ""
        steps: list[Step] = []
        seen: set[str] = set()

        for _ in range(self.max_steps):
            messages = [
                {"role": "system", "content": system},
                *self.bot.history,
                {"role": "user", "content": question},
            ]
            # Ép model vào format: mồi lượt assistant bằng "Thought:".
            messages.append({"role": "assistant", "content": f"{scratchpad}Thought:"})

            raw = self.bot.complete(messages, stop=["Observation:", "\nObservation:"])
            if not _THOUGHT_RE.match(raw.lstrip()):
                raw = f"Thought:{raw}"
            step = Step(raw=raw)
            thought = _THOUGHT_RE.search(raw)
            step.thought = thought.group("thought").strip() if thought else ""

            final = _FINAL_RE.search(raw)
            if final:
                step.observation = "<final>"
                steps.append(step)
                answer = final.group("answer").strip()
                self.bot.remember(question, answer)
                return ReActResult(answer=answer, steps=steps, retrieved=retrieved)

            action = _ACTION_RE.search(raw)
            if not action:
                # Không Action, không Final Answer -> coi cả output là câu trả lời.
                steps.append(step)
                answer = raw.strip()
                self.bot.remember(question, answer)
                return ReActResult(answer=answer, steps=steps, retrieved=retrieved)

            step.action = _tool_name(action.group("name"))
            try:
                step.action_input = _parse_args(action.group("args"))
                step.observation = self.registry.call(step.action, step.action_input)
                # Chặn lặp vô ích: gọi y hệt lần trước thì cảnh báo thay vì để model xoay vòng.
                key = f"{step.action}|{json.dumps(step.action_input, sort_keys=True, ensure_ascii=False)}"
                if key in seen:
                    step.observation += (
                        "\n[Cảnh báo] Đã gọi đúng tool này với đúng tham số này rồi. "
                        "Đổi hẳn truy vấn, đổi tool, hoặc chốt Final Answer."
                    )
                seen.add(key)
            except ValueError as exc:
                step.observation = f"Lỗi: {exc}"

            steps.append(step)
            scratchpad += f"{raw.rstrip()}\nObservation: {step.observation}\n"

        # Hết bước: ép model chốt câu trả lời từ những gì đã quan sát.
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
            {"role": "assistant", "content": scratchpad},
            {
                "role": "user",
                "content": "Hết số bước cho phép. Trả `Final Answer:` ngay dựa trên Observation đã có, nêu rõ phần còn thiếu.",
            },
        ]
        raw = self.bot.complete(messages)
        final = _FINAL_RE.search(raw)
        answer = final.group("answer").strip() if final else raw.strip()
        self.bot.remember(question, answer)
        return ReActResult(
            answer=answer, steps=steps, stopped_early=True, retrieved=retrieved
        )

    def reset(self) -> None:
        self.bot.reset()
