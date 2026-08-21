"""
Phase 1 verification script: drives every MCP tool through the real MCP
protocol (stdio) against a live FastAPI backend, and cross-checks each result
against a direct HTTP call to the same endpoint. Not part of the eval suite
(Phase 3) - this only checks "does each tool work and match the backend it
wraps", not grounding/narration quality.

Requires the FastAPI backend running (see README: `uvicorn api.main:app`).
Run: python -m mcp_server.verify_tools
"""
import asyncio
import json
import sys

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server.config import API_BASE_URL

def _identity(x):
    return x


def _wrap(key):
    return lambda x: {key: x}


CASES = [
    # tool_name, args, http_path, http_params, wrap(direct_json) -> expected_mcp_json
    ("get_accident_count", {"state": "BY", "year": 2022},
     "/aggregates/accidents", {"state": "BY", "year": 2022}, _identity),
    ("get_accidents_by_region", {"level": "state", "year": 2022, "limit": 5},
     "/aggregates/accidents/by-region", {"level": "state", "year": 2022, "limit": 5}, _wrap("items")),
    ("get_accident_hotspots", {"year": 2022, "state": "BY", "limit": 5},
     "/aggregates/hotspots", {"year": 2022, "state": "BY", "limit": 5}, _identity),
    ("get_accident_trend", {"state": "BY"},
     "/stats/trend", {"state": "BY"}, _identity),
    ("get_first_data_year", {},
     "/stats/first-year", {}, _identity),
    ("list_accidents", {"state": "BY", "year": 2022, "limit": 5},
     "/accidents", {"state": "BY", "year": 2022, "limit": 5}, _identity),
    ("get_data_sources", {},
     "/metadata/sources", {}, _wrap("sources")),
    ("get_import_runs", {},
     "/import-runs", {}, _wrap("runs")),
    ("resolve_region", {"name": "Bayern"},
     None, None, None),  # no direct HTTP equivalent - checked separately below
]


async def direct_call(path: str, params: dict) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()


async def main() -> int:
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    failures = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            tool_names = {t.name for t in listed.tools}
            print(f"Registered tools ({len(tool_names)}): {sorted(tool_names)}\n")

            expected = {name for name, *_ in CASES}
            if tool_names != expected:
                print(f"MISMATCH: expected {sorted(expected)}, got {sorted(tool_names)}")
                failures.append("tool set mismatch")

            for tool_name, args, http_path, http_params, wrap in CASES:
                print(f"--- {tool_name}({args}) ---")
                try:
                    result = await session.call_tool(tool_name, args)
                except Exception as e:
                    print(f"  MCP CALL FAILED: {e}")
                    failures.append(f"{tool_name}: call failed")
                    continue

                if result.isError:
                    print(f"  TOOL ERROR: {result.content}")
                    failures.append(f"{tool_name}: tool returned error")
                    continue

                text = result.content[0].text
                mcp_data = json.loads(text)
                print(f"  MCP result: {json.dumps(mcp_data)[:200]}")

                if http_path is None:
                    if not mcp_data.get("matches"):
                        print("  WARNING: resolve_region('Bayern') returned no matches")
                        failures.append("resolve_region: no matches for Bayern")
                    continue

                try:
                    direct_data = await direct_call(http_path, http_params)
                except Exception as e:
                    print(f"  DIRECT HTTP CALL FAILED: {e}")
                    failures.append(f"{tool_name}: direct http call failed")
                    continue

                expected_data = wrap(direct_data)
                if mcp_data != expected_data:
                    print(f"  MISMATCH vs direct HTTP call:\n    mcp={mcp_data}\n    http={expected_data}")
                    failures.append(f"{tool_name}: result mismatch")
                else:
                    print("  OK - matches direct HTTP call")

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)} issue(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All tools verified OK.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
