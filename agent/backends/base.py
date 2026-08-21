from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """One tool call from an assistant turn, normalized across backends.
    `id` is opaque - backends that don't have a real call id (Ollama) get one
    generated so the rest of the loop never needs to know the difference.
    """
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantTurn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class Backend:
    """A chat backend that can do tool-calling. Subclasses own their own wire
    format entirely - the orchestrator loop only ever sees AssistantTurn/ToolCall
    and the dict messages these methods hand back.
    """
    name: str
    use_compact_prompt: bool = False  # see agent/system_prompt.py:COMPACT_SYSTEM_PROMPT

    async def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        raise NotImplementedError

    def format_assistant_message(self, turn: AssistantTurn) -> dict:
        """How this backend expects its own prior turn echoed back into `messages`."""
        raise NotImplementedError

    def format_tool_result_message(self, tool_call: ToolCall, result: dict) -> dict:
        """How this backend expects a tool result appended to `messages`."""
        raise NotImplementedError
