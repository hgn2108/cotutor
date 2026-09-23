from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limit on fresh (non-cached) runs per client, protecting the shared quota."""

    def __init__(self, limit: int, window_s: float = 3600):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client: str) -> bool:
        now, q = time.monotonic(), self.hits[client]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
