import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_NULL_LIKE = {"null", "none", "undefined", ""}


def _strip_null_like(arguments: dict) -> dict:
    """Smaller local models (observed: llama3.2:3b) sometimes emit the literal
    string "null" for a parameter they mean to leave unset, instead of omitting
    it. Drop those keys entirely so the tool's own default applies - the
    alternative (passing the string through) can silently change query
    semantics on parameters without a safety net like `state` overriding `region`.
    """
    return {k: v for k, v in arguments.items() if not (isinstance(v, str) and v.strip().lower() in _NULL_LIKE)}


_REGION_FORMAT_HINT = (
    "Hint: region_ags must be a numeric AGS code, not a place name. Call "
    "resolve_region with the place name first to get the AGS code, then pass "
    "that AGS code as region_ags."
)
_UNKNOWN_STATE_HINT = (
    "Hint: call resolve_region with the place name to find the right AGS code "
    "or state abbreviation, rather than guessing one."
)


def _coach_error(raw_text: str) -> str | None:
    """A tool error alone (e.g. 'Unknown state' or a schema validation failure)
    is often enough for a capable model to self-correct, but smaller models were
    observed giving up instead of retrying with resolve_region (see Phase 3 eval:
    am-01 tried state="MUC" - an airport code, not a state abbreviation - got a
    clean error back, and then just stopped). Appending an explicit, mechanical
    hint for the specific failure pattern costs nothing on a model that would
    have figured it out anyway, and measurably helps one that wouldn't.
    """
    lowered = raw_text.lower()
    if "numeric ags" in lowered:
        return _REGION_FORMAT_HINT
    if "unknown state" in lowered or ("validation error" in lowered and "state" in lowered):
        return _UNKNOWN_STATE_HINT
    return None


class MCPToolClient:
    """Thin wrapper around the mcp_server subprocess: lists tools in the
    OpenAI/Ollama function-calling schema shape, and executes tool calls by name.
    """

    def __init__(self):
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolClient":
        params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def list_tools(self) -> list[dict]:
        """Returns tools in the Ollama/OpenAI function-calling schema:
        [{"type": "function", "function": {"name", "description", "parameters"}}]
        """
        result = await self._session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            }
            for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> tuple[dict, bool]:
        """Executes an MCP tool call. Returns (result_json, is_error).
        result_json is always a dict - either the tool's real JSON result, or
        {"error": "<message>"} when the tool itself reported an error.
        """
        arguments = _strip_null_like(arguments)
        result = await self._session.call_tool(name, arguments)
        text = result.content[0].text if result.content else "{}"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw_text": text}
        if result.isError:
            error_payload = {"error": parsed if isinstance(parsed, dict) else str(parsed)}
            raw_text = parsed.get("raw_text", "") if isinstance(parsed, dict) else str(parsed)
            hint = _coach_error(raw_text)
            if hint:
                error_payload["hint"] = hint
            return error_payload, True
        return parsed, False
