"""Render system prompt từ template Jinja."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

_env = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class ToolSignature:
    """Chữ ký tool đổ vào system prompt."""

    name: str
    description: str
    signature: str


def render_system_prompt(
    tool_signatures: Sequence[Any] | None = None,
    retrieved: Sequence[Any] | None = None,
    context: str = "",
    react: bool = False,
    max_steps: int = 6,
    template: str = "system.j2",
) -> str:
    """Đổ tool signature + chunk RAG + giao thức ReAct vào system prompt.

    `tool_signatures`: object có .name/.description/.signature (ToolSignature hoặc Tool).
    `retrieved`: object có .text/.source/.score (rag.retriever.Chunk).
    """
    return _env.get_template(template).render(
        tool_signatures=list(tool_signatures or []),
        retrieved=list(retrieved or []),
        context=context,
        react=react,
        max_steps=max_steps,
    )
