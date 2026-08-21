"""
Simple in-memory fixed-window rate limiter for agent/api.py. Deliberately
minimal (no Redis, no distributed state) - matches this project's stated scope
for the API wrapper ("minimal HTTP interface"), and is enough to stop a single
client from accidentally hammering a paid/rate-limited LLM backend through
this process, which is the actual risk this project has (Groq's free tier)
rather than large-scale abuse protection.
"""
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True
