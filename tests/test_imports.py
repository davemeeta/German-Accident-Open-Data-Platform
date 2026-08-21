"""
Import-sanity checks: every module in mcp_server/, agent/, and evals/ should
import cleanly with no live backend running. Catches broken imports, syntax
errors, and (for mcp_server.server) tool-registration errors, all without
needing the FastAPI data backend or an LLM key. This is not a substitute for
mcp_server/verify_tools.py or the eval suite (evals/run_eval.py), which check
actual behavior against a live backend and are not runnable in CI.
"""
import importlib


def test_mcp_server_registers_nine_tools():
    server = importlib.import_module("mcp_server.server")
    # FastMCP's tool manager keeps a private registry; the public list_tools()
    # coroutine needs a running session, so we just check the app constructs
    # and has the expected tool functions registered by name.
    tool_names = set(server.mcp._tool_manager._tools.keys())
    expected = {
        "get_accident_count", "get_accidents_by_region", "get_accident_hotspots",
        "get_accident_trend", "get_first_data_year", "list_accidents",
        "get_data_sources", "get_import_runs", "resolve_region",
    }
    assert tool_names == expected


def test_agent_modules_import():
    for mod in [
        "agent.config", "agent.grounding", "agent.system_prompt", "agent.session",
        "agent.trace_logger", "agent.mcp_client", "agent.orchestrator", "agent.cli",
        "agent.backends", "agent.backends.base", "agent.backends.groq_backend",
        "agent.backends.ollama_backend",
    ]:
        importlib.import_module(mod)


def test_evals_modules_import():
    for mod in ["evals.questions", "evals.grounding_check", "evals.run_eval"]:
        importlib.import_module(mod)


def test_agent_api_module_imports_without_starting_server():
    importlib.import_module("agent.api")
