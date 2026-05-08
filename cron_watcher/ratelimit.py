"""Per-job alert rate limiting with a sliding window counter."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class RateLimitConfig:
    enabled: bool = False
    max_alerts: int = 5          # max alerts per window
    window_seconds: int = 3600   # rolling window length in seconds


def ratelimit_config_from_dict(d: dict) -> RateLimitConfig:
    raw = d.get("ratelimit", {})
    return RateLimitConfig(
        enabled=bool(raw.get("enabled", False)),
        max_alerts=int(raw.get("max_alerts", 5)),
        window_seconds=int(raw.get("window_seconds", 3600)),
    )


@dataclass
class _JobWindow:
    timestamps: Deque[float] = field(default_factory=deque)

    def evict(self, cutoff: float) -> None:
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def count(self, cutoff: float) -> int:
        self.evict(cutoff)
        return len(self.timestamps)

    def record(self, ts: float) -> None:
        self.timestamps.append(ts)


class RateLimiter:
    """Tracks per-job alert counts within a rolling time window."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._windows: Dict[str, _JobWindow] = {}

    def _get_window(self, job: str) -> _JobWindow:
        if job not in self._windows:
            self._windows[job] = _JobWindow()
        return self._windows[job]

    def is_allowed(self, job: str, now: float | None = None) -> bool:
        """Return True if an alert for *job* is within the rate limit."""
        if not self.config.enabled:
            return True
        ts = now if now is not None else time.monotonic()
        cutoff = ts - self.config.window_seconds
        window = self._get_window(job)
        return window.count(cutoff) < self.config.max_alerts

    def record(self, job: str, now: float | None = None) -> None:
        """Record that an alert was sent for *job*."""
        ts = now if now is not None else time.monotonic()
        self._get_window(job).record(ts)

    def remaining(self, job: str, now: float | None = None) -> int:
        """How many more alerts are allowed for *job* in the current window."""
        if not self.config.enabled:
            return self.config.max_alerts
        ts = now if now is not None else time.monotonic()
        cutoff = ts - self.config.window_seconds
        used = self._get_window(job).count(cutoff)
        return max(0, self.config.max_alerts - used)
