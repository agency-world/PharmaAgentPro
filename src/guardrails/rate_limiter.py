"""Per-user and global rate limiting for the agent system."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger("guardrails.rate_limit")


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_in_seconds: float
    message: str = ""


class RateLimiter:
    """Sliding-window rate limiter for LLM requests."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self._window_seconds = 60.0
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str = "default") -> RateLimitResult:
        """Check if a request is allowed for the given user."""
        now = time.monotonic()
        window_start = now - self._window_seconds

        # Prune old requests
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > window_start
        ]

        current_count = len(self._requests[user_id])
        remaining = max(0, self.requests_per_minute - current_count)

        if current_count >= self.requests_per_minute:
            oldest = self._requests[user_id][0]
            reset_in = oldest - window_start
            logger.warning("Rate limit exceeded for user %s", user_id)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in_seconds=round(reset_in, 1),
                message=f"Rate limit exceeded. Try again in {reset_in:.0f}s.",
            )

        # Record the request
        self._requests[user_id].append(now)

        return RateLimitResult(
            allowed=True,
            remaining=remaining - 1,
            reset_in_seconds=0,
        )

    def get_usage(self, user_id: str = "default") -> dict[str, int]:
        """Get current usage stats for a user."""
        now = time.monotonic()
        window_start = now - self._window_seconds
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > window_start
        ]
        return {
            "current_requests": len(self._requests[user_id]),
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - len(self._requests[user_id])),
        }
