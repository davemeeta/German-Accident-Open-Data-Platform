import time

import httpx

from mcp_server.config import API_BASE_URL


class BackendError(Exception):
    """Raised when the FastAPI backend returns a non-2xx response.

    Carries the real status/detail through so the agent can surface an honest
    error instead of guessing why a tool call failed.
    """

    def __init__(self, status_code: int, detail, path: str):
        self.status_code = status_code
        self.detail = detail
        self.path = path
        super().__init__(f"{path} -> HTTP {status_code}: {detail}")


async def api_get(path: str, params: dict | None = None) -> tuple[dict, float]:
    """GET against the existing FastAPI backend. Returns (json_body, latency_ms).

    No retries, no result shaping: the caller gets exactly what the backend sent.
    """
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    start = time.monotonic()
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.get(path, params=clean_params)
    latency_ms = (time.monotonic() - start) * 1000

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise BackendError(resp.status_code, detail, path)

    return resp.json(), latency_ms
