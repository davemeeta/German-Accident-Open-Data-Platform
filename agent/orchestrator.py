import dataclasses
import json

from agent.backends import Backend, get_backend
from agent.config import MAX_TOOL_ITERATIONS
from agent.grounding import grounding_violations
from agent.mcp_client import MCPToolClient
from agent.session import Session
from agent.system_prompt import COMPACT_SYSTEM_PROMPT, SYSTEM_PROMPT
from agent.trace_logger import Timer, new_trace

_GROUNDING_RETRY_MESSAGE = (
    "Your previous answer stated number(s) that don't appear in any tool result "
    "you've received in this conversation: {violations}. Restate your answer "
    "using ONLY numbers that came from an actual tool call, call a tool if you "
    "still need one, or say explicitly that you cannot answer if no tool result "
    "supports it. Do not guess, estimate, or calculate a new number."
)

_GATE_FALLBACK_NARRATION = (
    "I can't confidently ground this answer in the actual data - my answer "
    "stated a number that didn't come from any tool result, even after I tried "
    "to correct it. Rather than guess, I'm going to stop here. Could you "
    "rephrase the question, or ask something I can verify against the data?"
)


def _prior_session_tool_results(session: Session | None) -> list[dict]:
    """Synthesizes tool_call-shaped entries from a session's earlier turns, so
    a follow-up question can legitimately cite a number established earlier in
    the same conversation without re-calling the tool that produced it - the
    per-turn trace only records tool calls made *this* turn, so without this
    the grounding gate would wrongly flag a correct, previously-grounded
    reference as fabricated.
    """
    if not session:
        return []
    extras = []
    for m in session.messages:
        if m.get("role") == "tool" and isinstance(m.get("content"), str):
            try:
                extras.append({"raw_result": json.loads(m["content"])})
            except json.JSONDecodeError:
                continue
    return extras


async def ask(
    question: str,
    mcp: MCPToolClient,
    backend: Backend | None = None,
    session: Session | None = None,
) -> tuple[str, str]:
    """Runs one question through the tool-calling loop against the given backend
    (defaults to config.DEFAULT_BACKEND). Every final answer is checked live by
    the same grounding logic the eval suite uses (agent/grounding.py) before
    it's returned - a violation triggers one corrective retry, and if that's
    still ungrounded, an honest fallback refusal is returned instead of ever
    handing back an unverified number.

    Pass `session` (agent/session.py) to continue a multi-turn conversation -
    the question is appended to the session's existing history instead of
    starting fresh, and follow-ups can reference earlier turns. Omit it for a
    one-shot question (each eval-suite question is always one-shot).
    Returns (narration_text, trace_log_path).
    """
    backend = backend or get_backend()
    tools = await mcp.list_tools()
    trace = new_trace(question, f"{backend.name}:{getattr(backend, 'model', '?')}")

    if session is not None and session.messages:
        messages = session.messages
        messages.append({"role": "user", "content": question})
    else:
        system_prompt = COMPACT_SYSTEM_PROMPT if backend.use_compact_prompt else SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

    session_extras = _prior_session_tool_results(session)
    gate_used = False
    gate_info: dict = {"triggered": False}

    def finish(narration: str) -> tuple[str, str]:
        if session is not None:
            session.messages = messages
        path = trace.finalize(narration, grounding_gate=gate_info if gate_info["triggered"] else None)
        return narration, path

    for _ in range(MAX_TOOL_ITERATIONS):
        turn = await backend.chat(messages, tools)
        if getattr(backend, "model_switched_from", None):
            # a configured model became unavailable mid-run and a fallback was
            # used (see GroqBackend._FALLBACK_MODELS) - reflect that in the
            # trace rather than silently recording the originally-requested model
            trace.model = f"{backend.name}:{backend.model}"
        messages.append(backend.format_assistant_message(turn))

        if not turn.tool_calls:
            trace_dict = dataclasses.asdict(trace)
            trace_dict["narration"] = turn.content
            trace_dict["tool_calls"] = trace_dict["tool_calls"] + session_extras
            violations = grounding_violations(question, trace_dict)

            if not violations:
                if gate_used:
                    gate_info["final_action"] = "retry_passed"
                    gate_info["final_narration"] = turn.content
                return finish(turn.content)

            if gate_used:
                gate_info["final_action"] = "fallback_used_after_retry"
                gate_info["retry_violations"] = violations
                gate_info["retry_narration"] = turn.content
                return finish(_GATE_FALLBACK_NARRATION)

            gate_used = True
            gate_info = {
                "triggered": True,
                "original_narration": turn.content,
                "original_violations": violations,
                "final_action": "pending",
            }
            messages.append({"role": "user", "content": _GROUNDING_RETRY_MESSAGE.format(violations=violations)})
            continue

        for tool_call in turn.tool_calls:
            with Timer() as t:
                result, is_error = await mcp.call_tool(tool_call.name, tool_call.arguments)
            trace.record_tool_call(tool_call.name, tool_call.arguments, result, t.elapsed_ms, is_error)
            messages.append(backend.format_tool_result_message(tool_call, result))

    narration = (
        "I wasn't able to finish answering this within the allotted number of "
        "tool-call steps. I don't want to guess, so I'm stopping here rather "
        "than giving an incomplete or invented answer."
    )
    return finish(narration)
