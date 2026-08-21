from agent.config import DEFAULT_BACKEND

from .base import AssistantTurn, Backend, ToolCall
from .groq_backend import GroqBackend, GroqConfigError, GroqRateLimitError, GroqTimeoutError
from .ollama_backend import OllamaBackend, OllamaUnavailableError

_BACKENDS = {"groq": GroqBackend, "ollama": OllamaBackend}


def get_backend(name: str | None = None) -> Backend:
    name = name or DEFAULT_BACKEND
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise ValueError(f"Unknown backend '{name}'. Choose from: {sorted(_BACKENDS)}") from None
    return cls()


__all__ = [
    "AssistantTurn",
    "Backend",
    "ToolCall",
    "GroqBackend",
    "GroqConfigError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "OllamaBackend",
    "OllamaUnavailableError",
    "get_backend",
]
