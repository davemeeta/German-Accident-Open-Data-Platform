"""
Unit tests for the core grounding primitive (agent/grounding.py). Pure logic,
no live backend or LLM needed - these run in CI. Contrast with evals/, which
needs a live database + API + LLM key and is not runnable in CI.
"""
from agent.grounding import collect_grounded_numbers, extract_numbers, grounding_violations


def test_extract_numbers_basic():
    assert extract_numbers("There were 44680 accidents.") == {"44680"}


def test_extract_numbers_comma_thousands():
    assert extract_numbers("There were 44,680 accidents.") == {"44680"}


def test_extract_numbers_unicode_narrow_nbsp_thousands():
    # observed from openai/gpt-oss-120b via Groq: "44 680" instead of "44,680"
    assert extract_numbers("There were 44 680 accidents.") == {"44680"}


def test_extract_numbers_trailing_sentence_period_not_swallowed():
    # regression: "...of 44680." must not become "44680." (with the period)
    assert extract_numbers("The result returned an accident_count of 44680.") == {"44680"}


def test_extract_numbers_markdown_list_markers_excluded():
    text = "Two matches:\n1. Frankfurt am Main - AGS 06412\n2. Frankfurt (Oder) - AGS 12053"
    numbers = extract_numbers(text)
    assert "1" not in numbers
    assert "2" not in numbers
    assert "06412" in numbers or "6412" in numbers  # leading zero handling is not normalized, just present
    assert "12053" in numbers


def test_collect_grounded_numbers_only_uses_raw_result_not_arguments():
    # hardened behavior: a number that only appears in tool call *arguments*
    # (e.g. an echoed request parameter like limit=20) must NOT count as
    # grounded - only numbers the tool actually *returned* do. Otherwise a
    # fabricated number could hide behind a coincidental argument value.
    trace = {
        "tool_calls": [{
            "arguments": {"state": "BY", "year": 2022, "limit": 20},
            "raw_result": {"query": {"state": "BY", "year": 2022}, "accident_count": 44680},
        }]
    }
    grounded = collect_grounded_numbers(trace)
    assert "44680" in grounded
    assert "2022" in grounded  # echoed inside raw_result's own "query" field, so still grounded
    assert "20" not in grounded  # only in arguments, never in raw_result


def test_grounding_violations_catches_fabricated_number():
    trace = {
        "tool_calls": [{
            "arguments": {"state": "BY", "year": 2022},
            "raw_result": {"accident_count": 44680},
        }],
        "narration": "There were 99999 accidents in Bavaria in 2022.",
    }
    violations = grounding_violations("How many accidents were there in Bavaria in 2022?", trace)
    assert violations == ["99999"]


def test_grounding_violations_allows_real_tool_result():
    trace = {
        "tool_calls": [{
            "arguments": {"state": "BY", "year": 2022},
            "raw_result": {"accident_count": 44680},
        }],
        "narration": "There were 44,680 accidents in Bavaria in 2022.",
    }
    violations = grounding_violations("How many accidents were there in Bavaria in 2022?", trace)
    assert violations == []


def test_grounding_violations_allows_question_echo():
    # a year the user typed themselves isn't an invented number, even if no
    # tool call happened to return it verbatim
    trace = {"tool_calls": [], "narration": "I don't have a tool that can answer that for 2022."}
    violations = grounding_violations("What happened in 2022?", trace)
    assert violations == []


def test_grounding_violations_coincidental_argument_no_longer_slips_through():
    # the exact blind spot the hardening in agent/grounding.py closed: "20"
    # only matches an echoed argument (limit=20), never a real result value
    trace = {
        "tool_calls": [{
            "arguments": {"state": "BY", "year": 2022, "limit": 20},
            "raw_result": {"query": {"state": "BY", "year": 2022}, "accident_count": 44680},
        }],
        "narration": "There were 20 accidents in Bavaria in 2022.",
    }
    violations = grounding_violations("How many accidents were there in Bavaria in 2022?", trace)
    assert violations == ["20"]
