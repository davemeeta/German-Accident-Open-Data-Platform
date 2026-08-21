"""
Core grounding primitive, used both live (agent/orchestrator.py, as a real
enforcement gate on every answer) and by the eval suite (evals/grounding_check.py,
which re-checks it mechanically after the fact). This module owns the logic;
evals/ imports from here rather than duplicating it, since the live gate is the
one that actually has to be correct in production - the eval is checking that
same code path, not a parallel implementation of it.
"""
import re

# Some models (observed: openai/gpt-oss-120b via Groq) format large numbers with
# a Unicode narrow no-break space (U+202F) or non-breaking space (U+00A0) as the
# thousands separator instead of a comma, e.g. "44 680". Both are treated as
# separator characters, same as a comma.
_NUMBER_RE = re.compile(r"-?\d[\d, \xa0]*(?:\.\d+)?")  # decimal point only counts if followed by a digit
_SEPARATORS = (",", " ", "\xa0")

# Markdown ordered-list markers ("1. ", "2) ") are not narrated data values - strip
# them before number extraction so list numbering doesn't register as an
# ungrounded number.
_LIST_MARKER_RE = re.compile(r"(?m)^\s*\d+[.)]\s+")


def extract_numbers(text: str) -> set[str]:
    text = _LIST_MARKER_RE.sub("", text or "")
    numbers = set()
    for m in _NUMBER_RE.findall(text):
        for sep in _SEPARATORS:
            m = m.replace(sep, "")
        numbers.add(m)
    return numbers


def collect_grounded_numbers(trace: dict) -> set[str]:
    """Every number that appeared in a tool call's raw RESULT across the whole
    trace - the only numbers the narration is allowed to state.

    Deliberately excludes tool call *arguments* (e.g. year=2022, limit=20) -
    those are numbers the model chose to send, not numbers a tool returned, and
    pooling them in would let a fabricated number slip through ungrounded just
    because it happens to coincide with an echoed request parameter (a real
    blind spot: a fabricated "20" could hide behind a coincidental limit=20).
    This loses no legitimate grounding in practice - every tool in this project
    echoes its actual query filters back inside raw_result too (e.g.
    {"query": {"state": "BY", "year": 2022}, "accident_count": ...} or
    {"limit": 5, "offset": 0, "items": [...]}), so a real, tool-confirmed
    parameter is still grounded via the result, not just the request.
    """
    numbers: set[str] = set()

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, bool):
            return
        elif isinstance(obj, (int, float)):
            numbers.add(str(obj))
        elif isinstance(obj, str):
            numbers.update(extract_numbers(obj))

    for call in trace.get("tool_calls", []):
        walk(call.get("raw_result"))
    return numbers


def grounding_violations(question_text: str, trace: dict) -> list[str]:
    """Numbers stated in the narration that trace to neither a tool result nor
    the question itself. Non-empty means a real grounding violation - an
    invented or calculated number.
    """
    narration_numbers = extract_numbers(trace.get("narration"))
    grounded = collect_grounded_numbers(trace)
    from_question = extract_numbers(question_text)
    return sorted(n for n in narration_numbers if n not in grounded and n not in from_question)
