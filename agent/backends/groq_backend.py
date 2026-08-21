import asyncio
import json

import httpx

from agent.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL

from .base import AssistantTurn, Backend, ToolCall

_MAX_RATE_LIMIT_RETRIES = 3
_DEFAULT_BACKOFF_SECONDS = 3.0
_MAX_BACKOFF_SECONDS = 30.0  # cap a large/malformed retry-after header from turning into a long silent wait
_HARD_TIMEOUT_SECONDS = 90.0  # backstop in case a connection hangs past its configured httpx timeout

# Groq's free-tier model lineup changes over time - `llama-3.3-70b-versatile`
# (this project's original default) was retired mid-project without warning,
# breaking the backend outright until manually diagnosed and swapped. This is
# an ordered fallback chain of other tool-calling-capable models (confirmed via
# GET /openai/v1/models -> supported_features includes "tools") so a future
# retirement degrades gracefully instead of hard-failing every request.
_FALLBACK_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b")


class GroqConfigError(Exception):
    pass


class GroqRateLimitError(Exception):
    pass


class GroqTimeoutError(Exception):
    pass


class GroqBackend(Backend):
    """Hosted, OpenAI-compatible chat completions. Free tier is rate-limited
    (30 req/min, 8K tokens/min for llama-3.3-70b-versatile at time of writing) -
    retries on 429 with backoff, honoring the `retry-after` header when present.
    """
    name = "groq"

    def __init__(self, model: str = GROQ_MODEL, base_url: str = GROQ_BASE_URL, api_key: str | None = GROQ_API_KEY):
        if not api_key:
            raise GroqConfigError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
                "and export it (e.g. `export GROQ_API_KEY=...`) before using the groq backend."
            )
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.model_switched_from: str | None = None  # set if a 404 forced a fallback (see _FALLBACK_MODELS)

    async def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        try:
            data = await asyncio.wait_for(self._chat_with_retries(messages, tools), timeout=_HARD_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            raise GroqTimeoutError(
                f"No response from Groq within {_HARD_TIMEOUT_SECONDS}s across all retries "
                "(connection likely hung rather than erroring cleanly)."
            ) from None

        choice = data["choices"][0]["message"]
        content = choice.get("content") or ""
        raw_calls = choice.get("tool_calls") or []

        tool_calls = []
        for call in raw_calls:
            fn = call["function"]
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(ToolCall(id=call["id"], name=fn["name"], arguments=args))

        return AssistantTurn(content=content, tool_calls=tool_calls)

    async def _chat_with_retries(self, messages: list[dict], tools: list[dict]) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0, headers=headers) as client:
            candidates = [self.model] + [m for m in _FALLBACK_MODELS if m != self.model]
            for model in candidates:
                payload = {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto"}
                data = await self._post_with_rate_limit_retry(client, payload)
                if data is not None:
                    if model != self.model:
                        self.model_switched_from = self.model
                        self.model = model
                    return data
            raise GroqConfigError(
                f"None of the candidate models are available: {candidates}. "
                "Groq's free-tier lineup may have changed - check https://console.groq.com/docs/models "
                "and update agent/backends/groq_backend.py's _FALLBACK_MODELS."
            )

    async def _post_with_rate_limit_retry(self, client: httpx.AsyncClient, payload: dict) -> dict | None:
        """Returns the parsed response, or None if this model isn't available
        (404 model_not_found) so the caller can try the next fallback candidate.
        """
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            resp = await client.post("/chat/completions", json=payload)
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                if attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise GroqRateLimitError(resp.text)
                try:
                    delay = float(resp.headers.get("retry-after", _DEFAULT_BACKOFF_SECONDS))
                except ValueError:
                    delay = _DEFAULT_BACKOFF_SECONDS
                await asyncio.sleep(min(delay, _MAX_BACKOFF_SECONDS))
                continue
            resp.raise_for_status()
            return resp.json()
        raise GroqRateLimitError("exhausted retries")  # unreachable given the loop above, but keeps mypy/readers honest

    def format_assistant_message(self, turn: AssistantTurn) -> dict:
        msg = {"role": "assistant", "content": turn.content or None}
        if turn.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in turn.tool_calls
            ]
        return msg

    def format_tool_result_message(self, tool_call: ToolCall, result: dict) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.name,
            "content": json.dumps(result, ensure_ascii=False),
        }
