"""
Runs the full eval suite (evals/questions.py) through the live agent and
reports pass/fail honestly, per question and by category. Requires the
FastAPI backend running on :8000, and the chosen LLM backend configured
(GROQ_API_KEY for groq, `ollama serve` + pulled model for ollama).

Usage:
    python -m evals.run_eval                      # uses config.DEFAULT_BACKEND (groq)
    python -m evals.run_eval ollama
    python -m evals.run_eval groq --variance sl-01,am-01,na-01 --repeats 3
        # LLM output is stochastic - a single run (above) tells you pass/fail
        # for one trial per question, not how stable that result is. This mode
        # re-runs a chosen subset multiple times and reports whether the
        # outcome was consistent, so the headline pass rate isn't read as more
        # certain than a single-trial measurement actually supports.
"""
import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agent.backends import get_backend
from agent.mcp_client import MCPToolClient
from agent.orchestrator import ask
from evals.grounding_check import evaluate
from evals.questions import QUESTIONS

REPORT_DIR = Path(__file__).resolve().parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


async def run(backend_name: str | None = None) -> dict:
    backend = get_backend(backend_name)
    print(f"Running {len(QUESTIONS)} questions against {backend.name}:{backend.model}\n")

    results = []
    async with MCPToolClient() as mcp:
        for q in QUESTIONS:
            print(f"[{q.id}] {q.category}: {q.question}")
            try:
                narration, trace_path = await ask(q.question, mcp, backend)
                trace = json.loads(Path(trace_path).read_text())
                trace["_trace_path"] = trace_path
                result = evaluate(q, trace)
            except Exception as e:
                result = {
                    "id": q.id, "category": q.category, "question": q.question,
                    "narration": None, "tool_call_count": 0, "passed": False,
                    "reasons": [f"agent error: {type(e).__name__}: {e}"],
                    "trace_path": None,
                }
            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"  {status}" + (f" - {result['reasons']}" if result["reasons"] else ""))

    report = build_report(backend, results)
    out_path = REPORT_DIR / f"eval-{backend.name}-{int(time.time())}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print_summary(report)
    print(f"\nFull report: {out_path}")
    return report


def build_report(backend, results: list[dict]) -> dict:
    by_category: dict[str, dict] = {}
    for r in results:
        bucket = by_category.setdefault(r["category"], {"total": 0, "passed": 0, "failures": []})
        bucket["total"] += 1
        if r["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failures"].append(r)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    latencies = [r["total_tool_latency_ms"] for r in results if "total_tool_latency_ms" in r]
    return {
        "backend": f"{backend.name}:{backend.model}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": total,
        "passed": passed,
        "failed": total - passed,
        "failure_rate": round((total - passed) / total, 3) if total else None,
        "tool_latency_ms": {
            "total": round(sum(latencies), 1),
            "avg_per_question": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "max": round(max(latencies), 1) if latencies else None,
        },
        "by_category": by_category,
        "results": results,
    }


async def run_variance_check(backend_name: str | None, question_ids: list[str], repeats: int = 3) -> dict:
    """Re-runs each given question `repeats` times to measure how stable
    pass/fail is - the main eval run tries each question exactly once, which
    tells you nothing about whether that single trial was representative of a
    stochastic model's typical behavior or an outlier in either direction.
    """
    backend = get_backend(backend_name)
    qmap = {q.id: q for q in QUESTIONS}
    print(f"Variance check: {len(question_ids)} question(s) x {repeats} runs against {backend.name}:{backend.model}\n")

    variance: dict[str, dict] = {}
    async with MCPToolClient() as mcp:
        for qid in question_ids:
            q = qmap[qid]
            outcomes = []
            for i in range(repeats):
                try:
                    narration, trace_path = await ask(q.question, mcp, backend)
                    trace = json.loads(Path(trace_path).read_text())
                    trace["_trace_path"] = trace_path
                    outcomes.append(evaluate(q, trace)["passed"])
                except Exception:
                    outcomes.append(False)
                print(f"  [{qid}] run {i + 1}/{repeats}: {'PASS' if outcomes[-1] else 'FAIL'}")
            consistent = len(set(outcomes)) == 1
            variance[qid] = {
                "question": q.question,
                "outcomes": outcomes,
                "consistent": consistent,
                "pass_rate": sum(outcomes) / len(outcomes),
            }
            tag = "CONSISTENT" if consistent else "INCONSISTENT"
            print(f"  -> {qid}: {tag} ({sum(outcomes)}/{repeats} passed)\n")

    out_path = REPORT_DIR / f"variance-{backend.name}-{int(time.time())}.json"
    out_path.write_text(json.dumps(variance, indent=2, ensure_ascii=False))
    inconsistent = [qid for qid, v in variance.items() if not v["consistent"]]
    print("=" * 70)
    print(f"Variance summary: {len(inconsistent)}/{len(question_ids)} question(s) gave inconsistent results across {repeats} runs")
    if inconsistent:
        print(f"  Inconsistent: {inconsistent}")
    print(f"Variance report: {out_path}")
    return variance


def print_summary(report: dict) -> None:
    print("\n" + "=" * 70)
    print(f"EVAL SUMMARY - backend: {report['backend']}")
    print(
        f"Total: {report['total_questions']}  Passed: {report['passed']}  "
        f"Failed: {report['failed']}  Failure rate: {report['failure_rate']:.1%}"
    )
    lat = report.get("tool_latency_ms") or {}
    if lat.get("avg_per_question") is not None:
        print(f"Tool latency: avg {lat['avg_per_question']}ms/question, max {lat['max']}ms, total {lat['total']}ms")
    print("-" * 70)
    for cat, data in sorted(report["by_category"].items()):
        print(f"  {cat:16s}  {data['passed']}/{data['total']} passed")
        for f in data["failures"]:
            print(f"      FAIL [{f['id']}] {f['reasons']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grounding eval runner")
    parser.add_argument("backend", nargs="?", default=None, choices=["groq", "ollama"])
    parser.add_argument("--variance", help="Comma-separated question IDs to repeat-test instead of running the full suite")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per question in --variance mode (default: 3)")
    args = parser.parse_args()

    if args.variance:
        ids = [s.strip() for s in args.variance.split(",") if s.strip()]
        asyncio.run(run_variance_check(args.backend, ids, args.repeats))
    else:
        asyncio.run(run(args.backend))
