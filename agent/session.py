"""
Multi-turn conversation state. A Session just holds the growing message
history so a follow-up question ("no, I meant the district") continues the
same conversation instead of starting fresh - orchestrator.ask() appends to
session.messages and persists it back after each turn.

A session is pinned to one backend for its lifetime: the message history
contains that backend's own wire-format conventions (e.g. Groq's
tool_call_id-keyed tool results vs Ollama's id-less ones), so switching
backends mid-session would produce a history the new backend can't parse.
"""
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)


class SessionStore:
    """In-memory session registry for the HTTP API (agent/api.py). Sessions
    live only for the process lifetime - no persistence, matching this
    project's "minimal" scope for the interface layer.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        session = Session(id=session_id) if session_id else Session()
        self._sessions[session.id] = session
        return session
