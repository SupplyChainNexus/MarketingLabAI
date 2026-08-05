"""Small process-local rate limiter for the single-instance private pilot."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimitExceeded(RuntimeError):
    pass


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate-limit values must be positive.")
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = self.clock()
        events = self._events[key]
        threshold = now - self.window_seconds
        while events and events[0] <= threshold:
            events.popleft()
        if len(events) >= self.limit:
            raise RateLimitExceeded("Request rate limit exceeded.")
        events.append(now)
