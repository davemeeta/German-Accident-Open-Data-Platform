import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from agent.config import LOG_DIR, MAX_TRACE_FILES


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict
    latency_ms: float
    raw_result: dict
    is_error: bool


@dataclass
class ConversationTrace:
    trace_id: str
    question: str
    model: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    narration: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    grounding_gate: dict | None = None

    def record_tool_call(self, name: str, arguments: dict, raw_result: dict, latency_ms: float, is_error: bool) -> None:
        self.tool_calls.append(ToolCallRecord(name, arguments, latency_ms, raw_result, is_error))

    def finalize(self, narration: str, grounding_gate: dict | None = None) -> str:
        """Sets the final narration and writes the full trace to LOG_DIR as JSON.
        `grounding_gate` records whether the live grounding check caught a
        violation before this narration was returned (see orchestrator.ask()).
        Returns the path written to.
        """
        self.narration = narration
        self.grounding_gate = grounding_gate
        payload = asdict(self)
        path = LOG_DIR / f"{self.trace_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        _rotate_logs()
        return str(path)


def _rotate_logs() -> None:
    """Keeps only the MAX_TRACE_FILES most-recently-written trace files, so
    agent/logs/ doesn't grow unbounded over a long-running deployment. Cheap
    to call on every write since it only lists+sorts the directory, no content
    is read.
    """
    files = sorted(LOG_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[MAX_TRACE_FILES:]:
        stale.unlink(missing_ok=True)


def new_trace(question: str, model: str) -> ConversationTrace:
    return ConversationTrace(trace_id=f"{int(time.time())}-{uuid.uuid4().hex[:8]}", question=question, model=model)


class Timer:
    """Context manager returning elapsed milliseconds via .elapsed_ms after exit."""

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.monotonic() - self._start) * 1000
