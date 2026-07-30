"""CLI chat: uv run python -m src.chatbot [--react] [--trace]"""

import argparse
import sys

from .chatbot import Chatbot
from .mock.rag import NullRetriever
from .mock.tools import ToolRegistry, make_search_docs
from .react import ReActAgent


def main() -> None:
    # Console Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="chatbot")
    parser.add_argument("--react", action="store_true", help="chạy vòng ReAct có tool")
    parser.add_argument("--trace", action="store_true", help="in Thought/Action/Observation")
    parser.add_argument("--max-steps", type=int, default=6)
    args = parser.parse_args()

    # Đổi NullRetriever thành retriever thật khi index xong.
    retriever = NullRetriever()
    bot = Chatbot(retriever=retriever)
    registry = ToolRegistry([make_search_docs(retriever)])
    agent = ReActAgent(registry, chatbot=bot, max_steps=args.max_steps) if args.react else None

    mode = "ReAct" if args.react else "chat"
    print(f"[{mode}] {bot.settings.model} @ {bot.settings.base_url}")
    print("Gõ 'exit' để thoát, 'reset' để xoá lịch sử.\n")

    while True:
        try:
            user = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user in {"exit", "quit"}:
            break
        if user == "reset":
            (agent or bot).reset()
            print("Đã xoá lịch sử.\n")
            continue

        if agent:
            result = agent.run(user)
            if args.trace:
                print(f"  RAG pre-retrieve: {len(result.retrieved)} chunk")
                for chunk in result.retrieved:
                    print(f"      [{chunk.source}] score={chunk.score:.3f} {chunk.text[:80]}")
                for i, step in enumerate(result.steps, 1):
                    print(f"  [{i}] Thought: {step.thought}")
                    if step.action:
                        print(f"      Action: {step.action} {step.action_input}")
                        print(f"      Observation: {step.observation[:300]}")
            if result.stopped_early:
                print("  (hết số bước cho phép)")
            print(f"Bot: {result.answer}\n")
        else:
            print("Bot: ", end="", flush=True)
            for token in bot.stream(user):
                print(token, end="", flush=True)
            print("\n")


if __name__ == "__main__":
    main()
