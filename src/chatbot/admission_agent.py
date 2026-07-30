from .agent_tools import build_registry
from .chatbot import Chatbot
from .config import Settings
from .prompt import render_policy
from .rag_bridge import NO_GROUNDING_THRESHOLD, ChromaRetriever
from .react import ReActAgent

ADMISSION_POLICY = render_policy(NO_GROUNDING_THRESHOLD)


def build_admission_agent(
    settings: Settings | None = None,
    retriever: ChromaRetriever | None = None,
    max_steps: int = 6,
    top_k: int = 5,
) -> ReActAgent:
    retriever = retriever or ChromaRetriever()
    registry = build_registry(retriever)
    bot = Chatbot(
        settings=settings,
        retriever=retriever,
        context=ADMISSION_POLICY,
        top_k=top_k,
        grounding_threshold=NO_GROUNDING_THRESHOLD,
    )
    # Không còn tool tìm kiếm, nên chunk phải được đổ sẵn vào prompt.
    return ReActAgent(registry, chatbot=bot, max_steps=max_steps, prefetch_rag=True)


__all__ = ["ADMISSION_POLICY", "build_admission_agent"]
