"""Generic in-memory sliding-window rate limiter.

single-process, in-memory — same limitation as the original
login limiter it's factored out of (see auth.py history). Behind multiple
workers/replicas this needs Redis; fine for a portfolio demo on one Dokku
container.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: float, message: str):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.message = message
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = [t for t in self._hits[key] if now - t < self.window_seconds]
        if len(hits) >= self.max_attempts:
            self._hits[key] = hits
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=self.message,
            )
        hits.append(now)
        self._hits[key] = hits
