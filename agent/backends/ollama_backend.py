import json

import httpx

from agent.config import OLLAMA_BASE_URL, OLLAMA_MODEL

from .base import AssistantTurn, Backend, ToolCall


class OllamaUnavailableError(Exception):
    pass


class OllamaBackend(Backend):
    """Local, free, no external dependency - but Ollama's tool_calls have no
    call id, so results are matched back to calls by order, not by id.
    """
    name = "ollama"
    use_compact_prompt = True  # measured: full system prompt + full tool schema breaks tool-calling on small local models

    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url

    async def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            try:
                resp = await client.post(
                    "/api/chat",
                    json={"model": self.model, "messages": messages, "tools": tools, "stream": False},
                )
            except httpx.ConnectError as e:
                raise OllamaUnavailableError(
                    f"Could not reach Ollama at {self.base_url}. Is `ollama serve` running?"
                ) from e
            resp.raise_for_status()
            data = resp.json()

        message = data["message"]
        content = message.get("content") or ""
        raw_calls = message.get("tool_calls") or []

        tool_calls = []
        for i, call in enumerate(raw_calls):
            fn = call["function"]
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(ToolCall(id=f"ollama_call_{i}", name=fn["name"], arguments=args))

        return AssistantTurn(content=content, tool_calls=tool_calls)

    def format_assistant_message(self, turn: AssistantTurn) -> dict:
        msg = {"role": "assistant", "content": turn.content}
        if turn.tool_calls:
            msg["tool_calls"] = [
                {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in turn.tool_calls
            ]
        return msg

    def format_tool_result_message(self, tool_call: ToolCall, result: dict) -> dict:
        return {"role": "tool", "content": json.dumps(result, ensure_ascii=False)}
