"""
Minimal HTTP wrapper around the agent, for programmatic/scripted use alongside
the CLI (agent/cli.py). One MCPToolClient subprocess is kept alive for the
life of the server rather than respawned per request.

Requires the FastAPI *data* backend running separately (uvicorn api.main:app
on :8000 - unmodified, existing project). This is a different app, on a
different port, that talks to that one as a client.

Usage:
    uvicorn agent.api:app --port 8001
    curl -X POST localhost:8001/ask -H 'Content-Type: application/json' \
        -d '{"question": "How many accidents were there in Bavaria in 2022?"}'

    # multi-turn: pass back the session_id from the first response to continue
    curl -X POST localhost:8001/ask -H 'Content-Type: application/json' \
        -d '{"question": "What about 2019 instead?", "session_id": "<from first response>"}'
"""
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.backends import get_backend
from agent.mcp_client import MCPToolClient
from agent.orchestrator import ask
from agent.rate_limit import RateLimiter
from agent.session import SessionStore

_mcp_client: Optional[MCPToolClient] = None
_sessions = SessionStore()
_rate_limiter = RateLimiter(
    max_requests=int(os.environ.get("UNFALLATLAS_API_RATE_LIMIT", "20")),
    window_seconds=60.0,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_client
    _mcp_client = await MCPToolClient().__aenter__()
    try:
        yield
    finally:
        await _mcp_client.__aexit__(None, None, None)
        _mcp_client = None


app = FastAPI(title="Unfallatlas Agent", version="1.0.0", lifespan=lifespan)
# Same permissive policy as the data API (src/api/main.py) - this is a public-data
# read-only endpoint, not something holding credentials, so matching that existing
# choice rather than introducing a stricter one just for this new surface.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AskRequest(BaseModel):
    question: str
    backend: Optional[str] = None  # "groq" | "ollama" - defaults to config.DEFAULT_BACKEND
    session_id: Optional[str] = None  # omit to start a new conversation; pass back to continue one


class AskResponse(BaseModel):
    narration: str
    trace_path: str
    backend: str
    grounding_gate_triggered: bool
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(client_ip):
        raise HTTPException(429, "Rate limit exceeded - max 20 requests/minute per client. Retry later.")

    try:
        backend = get_backend(req.backend)
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}")

    session = _sessions.get_or_create(req.session_id)

    try:
        narration, trace_path = await ask(req.question, _mcp_client, backend, session)
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}")

    trace = json.loads(open(trace_path).read())
    gate = trace.get("grounding_gate")

    return AskResponse(
        narration=narration,
        trace_path=trace_path,
        backend=f"{backend.name}:{backend.model}",
        grounding_gate_triggered=bool(gate and gate.get("triggered")),
        session_id=session.id,
    )
