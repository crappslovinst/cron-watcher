"""Alert throttling: suppress repeated alerts for the same job within a time window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    window_seconds: int = 300  # 5 minutes default
    max_alerts_per_window: int = 3


@dataclass
class _JobThrottleState:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class AlertThrottle:
    """Track per-job alert counts and suppress when over the limit."""

    def __init__(self, config: ThrottleConfig) -> None:
        self._config = config
        self._state: Dict[str, _JobThrottleState] = {}

    def _get_state(self, job: str) -> _JobThrottleState:
        now = time.monotonic()
        st = self._state.get(job)
        if st is None:
            st = _JobThrottleState(window_start=now)
            self._state[job] = st
        elif now - st.window_start >= self._config.window_seconds:
            # Reset window
            st.count = 0
            st.window_start = now
        return st

    def should_send(self, job: str) -> bool:
        """Return True if an alert for *job* should be sent right now."""
        st = self._get_state(job)
        return st.count < self._config.max_alerts_per_window

    def record(self, job: str) -> None:
        """Record that an alert was sent for *job*."""
        st = self._get_state(job)
        st.count += 1

    def remaining(self, job: str) -> int:
        """Return how many more alerts are allowed for *job* in the current window."""
        st = self._get_state(job)
        return max(0, self._config.max_alerts_per_window - st.count)

    def reset(self, job: Optional[str] = None) -> None:
        """Clear throttle state for a specific job or all jobs."""
        if job is None:
            self._state.clear()
        else:
            self._state.pop(job, None)


def throttle_config_from_dict(d: dict) -> ThrottleConfig:
    return ThrottleConfig(
        window_seconds=int(d.get("window_seconds", 300)),
        max_alerts_per_window=int(d.get("max_alerts_per_window", 3)),
    )
