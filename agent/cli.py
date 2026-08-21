"""
One-shot / interactive CLI for the agent. Requires the FastAPI backend running
(uvicorn api.main:app on :8000). Default LLM backend is Groq (needs GROQ_API_KEY);
pass --backend ollama to use a local Ollama model instead (see agent/config.py).

Usage:
    python -m agent.cli "How many accidents were there in Bavaria in 2022?"
    python -m agent.cli --backend ollama "How many accidents were there in Bavaria in 2022?"
    python -m agent.cli   # interactive mode: blank line to quit, /new to reset the conversation

Interactive mode is a real multi-turn conversation, not repeated one-shot
questions - a follow-up like "what about 2019 instead?" resolves against the
same session, so it doesn't need to restate the state/place name.
"""
import argparse
import asyncio

from agent.backends import get_backend
from agent.backends.base import Backend
from agent.mcp_client import MCPToolClient
from agent.orchestrator import ask
from agent.session import Session


async def run_one(question: str, backend: Backend) -> None:
    async with MCPToolClient() as mcp:
        narration, path = await _safe_ask(question, mcp, backend)
        if narration is not None:
            print(narration)
            print(f"\n[trace: {path}]")


async def run_interactive(backend: Backend) -> None:
    session = Session()
    async with MCPToolClient() as mcp:
        while True:
            try:
                question = input("> ").strip()
            except EOFError:
                break
            if not question:
                break
            if question == "/new":
                session = Session()
                print("[new conversation]\n")
                continue
            narration, path = await _safe_ask(question, mcp, backend, session)
            if narration is not None:
                print(narration)
                print(f"[trace: {path}]\n")


async def _safe_ask(
    question: str, mcp: MCPToolClient, backend: Backend, session: Session | None = None
) -> tuple[str | None, str | None]:
    try:
        return await ask(question, mcp, backend, session)
    except Exception as e:  # backend-config/connectivity/rate-limit errors
        print(f"ERROR ({type(e).__name__}): {e}")
        return None, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Unfallatlas natural-language agent CLI")
    parser.add_argument("question", nargs="*", help="Question to ask (omit for interactive mode)")
    parser.add_argument("--backend", choices=["groq", "ollama"], default=None, help="LLM backend (default: config.DEFAULT_BACKEND, i.e. groq)")
    args = parser.parse_args()

    try:
        backend = get_backend(args.backend)
    except Exception as e:
        print(f"ERROR ({type(e).__name__}): {e}")
        return
    print(f"[backend: {backend.name}:{backend.model}]")

    if args.question:
        asyncio.run(run_one(" ".join(args.question), backend))
    else:
        asyncio.run(run_interactive(backend))


if __name__ == "__main__":
    main()
