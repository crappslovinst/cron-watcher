"""Module-level singleton helpers for RateLimiter."""
from __future__ import annotations

from typing import List, Optional

from cron_watcher.log_parser import CronEvent
from cron_watcher.ratelimit import RateLimitConfig, RateLimiter

_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Return the shared RateLimiter instance, creating it if necessary."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(config or RateLimitConfig())
    return _limiter


def reset_rate_limiter(config: Optional[RateLimitConfig] = None) -> None:
    """Discard the current instance (used in tests or on config reload)."""
    global _limiter
    _limiter = RateLimiter(config or RateLimitConfig())


def ratelimited_failures(
    events: List[CronEvent],
    config: Optional[RateLimitConfig] = None,
) -> List[CronEvent]:
    """Filter *events* to those that pass the per-job rate limit.

    Side-effect: allowed events are recorded so subsequent calls
    for the same job correctly count against the window.
    """
    limiter = get_rate_limiter(config)
    allowed: List[CronEvent] = []
    for ev in events:
        job = ev.job or ""
        if limiter.is_allowed(job):
            limiter.record(job)
            allowed.append(ev)
    return allowed
