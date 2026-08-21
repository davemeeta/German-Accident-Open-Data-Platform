"""
Mechanical checks applied to every eval trace. Two concerns, kept separate:

1. Grounding: does every number in the narration trace back to a real tool
   result (or the question itself, e.g. echoing a year the user typed)? This
   is the hard, non-negotiable check - any violation is a real finding
   regardless of category. The actual number-extraction/grounding logic lives
   in agent/grounding.py, the same module the live orchestrator uses to gate
   responses in production - this file re-checks that same code path after the
   fact, rather than reimplementing it, so eval results reflect what
   production actually enforces.
2. Correctness / expected behavior: for lookup-style questions, were the
   actual ground-truth numbers stated? For ambiguous/no-answer questions, did
   the response ask for clarification / refuse, rather than guessing?

The phrase-matching in (2) is a heuristic, not a proof - it will produce some
false negatives on correctly-behaving responses phrased in an unanticipated
way. That's disclosed in the eval report rather than hidden; borderline cases
should be spot-checked by reading the narration directly (each report row
includes it).
"""
from agent.grounding import collect_grounded_numbers, extract_numbers, grounding_violations

__all__ = ["collect_grounded_numbers", "extract_numbers", "grounding_violations", "evaluate"]


def check_correctness(expected_numbers: list[str], trace: dict) -> tuple[bool, str]:
    narration_numbers = extract_numbers(trace.get("narration"))
    missing = [n for n in expected_numbers if n not in narration_numbers]
    if missing:
        return False, f"missing expected number(s): {missing}"
    return True, ""


_REFUSAL_PHRASES = [
    "don't have a tool", "do not have a tool", "doesn't have a tool",
    "no tool", "not able to answer", "can't answer", "cannot answer",
    "not available", "i can't provide", "i cannot provide",
    "there is no tool", "no data on", "not tracked", "isn't tracked",
    "don't have access to", "not something i can", "unable to answer",
    "could not be", "couldn't be", "not provided", "is not provided",
]


def check_refusal(trace: dict) -> tuple[bool, str]:
    narration = (trace.get("narration") or "").lower()
    if any(p in narration for p in _REFUSAL_PHRASES):
        return True, ""
    return False, "narration does not contain an explicit refusal phrase"


_DISAMBIGUATION_PHRASES = [
    "which one", "which of these", "which do you mean", "did you mean",
    "could you clarify", "please specify", "let me know which",
    "which district", "which region", "which municipality",
    "do you want", "could you confirm", "please let me know",
]


def check_disambiguation(trace: dict) -> tuple[bool, str]:
    narration = (trace.get("narration") or "").lower()
    if any(p in narration for p in _DISAMBIGUATION_PHRASES):
        return True, ""
    return False, "narration does not ask for clarification"


def evaluate(question, trace: dict) -> dict:
    """question: an evals.questions.EvalQuestion. Returns a result dict with
    `passed` and a list of human-readable `reasons` for any failure.
    """
    reasons: list[str] = []

    violations = grounding_violations(question.question, trace)
    if violations:
        reasons.append(f"ungrounded number(s) in narration: {violations}")

    if question.expected_behavior == "refuse":
        ok, why = check_refusal(trace)
        if not ok:
            reasons.append(why)
    elif question.expected_behavior == "disambiguate":
        ok, why = check_disambiguation(trace)
        if not ok:
            reasons.append(why)
    elif question.expected_numbers:
        ok, why = check_correctness(question.expected_numbers, trace)
        if not ok:
            reasons.append(why)

    tool_latencies = [c.get("latency_ms", 0) for c in trace.get("tool_calls", [])]
    return {
        "id": question.id,
        "category": question.category,
        "question": question.question,
        "narration": trace.get("narration"),
        "tool_call_count": len(trace.get("tool_calls", [])),
        "total_tool_latency_ms": round(sum(tool_latencies), 1),
        "passed": len(reasons) == 0,
        "reasons": reasons,
        "trace_path": trace.get("_trace_path"),
    }
