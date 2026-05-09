"""Exponential back-off tracker for per-job alert suppression.

When a job fails repeatedly the back-off multiplier grows so that
alerts become progressively less frequent, giving operators breathing
room without losing visibility entirely.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BackoffConfig:
    enabled: bool = True
    base_delay: float = 60.0        # seconds before the 2nd alert
    multiplier: float = 2.0
    max_delay: float = 3600.0       # cap at 1 hour
    reset_after: float = 86400.0    # forget state after 24 h of silence


def backoff_config_from_dict(d: dict) -> BackoffConfig:
    raw = d.get("backoff", {})
    return BackoffConfig(
        enabled=bool(raw.get("enabled", True)),
        base_delay=float(raw.get("base_delay", 60.0)),
        multiplier=float(raw.get("multiplier", 2.0)),
        max_delay=float(raw.get("max_delay", 3600.0)),
        reset_after=float(raw.get("reset_after", 86400.0)),
    )


@dataclass
class _JobBackoffState:
    attempt: int = 0
    next_allowed: float = 0.0
    last_alert: float = 0.0


@dataclass
class BackoffTracker:
    config: BackoffConfig
    _states: Dict[str, _JobBackoffState] = field(default_factory=dict)

    def _get(self, job: str) -> _JobBackoffState:
        return self._states.setdefault(job, _JobBackoffState())

    def is_allowed(self, job: str, now: Optional[float] = None) -> bool:
        """Return True if an alert for *job* should be sent right now."""
        if not self.config.enabled:
            return True
        now = now if now is not None else time.monotonic()
        st = self._get(job)
        # Reset stale state
        if st.last_alert and (now - st.last_alert) >= self.config.reset_after:
            self._states.pop(job, None)
            return True
        return now >= st.next_allowed

    def record_alert(self, job: str, now: Optional[float] = None) -> None:
        """Call after an alert is dispatched to advance the back-off window."""
        if not self.config.enabled:
            return
        now = now if now is not None else time.monotonic()
        st = self._get(job)
        delay = min(
            self.config.base_delay * (self.config.multiplier ** st.attempt),
            self.config.max_delay,
        )
        st.attempt += 1
        st.next_allowed = now + delay
        st.last_alert = now

    def reset_job(self, job: str) -> None:
        """Manually clear back-off state for a job (e.g. after it succeeds)."""
        self._states.pop(job, None)
