"""Rate-limited notification gate — prevents alert storms."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class NotifierState:
    """Tracks per-job notification history."""
    last_notified: Dict[str, float] = field(default_factory=dict)
    suppressed_count: Dict[str, int] = field(default_factory=dict)


class RateLimitedNotifier:
    """Wraps dispatch_alerts with a per-job cooldown.

    Args:
        cooldown_seconds: Minimum seconds between alerts for the same job.
        dispatch_fn: Callable with the same signature as dispatch_alerts.
    """

    def __init__(self, cooldown_seconds: int = 300, dispatch_fn=None):
        if dispatch_fn is None:
            from cron_watcher.alerter import dispatch_alerts
            dispatch_fn = dispatch_alerts
        self._cooldown = cooldown_seconds
        self._dispatch = dispatch_fn
        self._state = NotifierState()

    # ------------------------------------------------------------------
    def should_notify(self, job: str) -> bool:
        """Return True if the cooldown has elapsed for *job*."""
        last = self._state.last_notified.get(job)
        if last is None:
            return True
        return (time.monotonic() - last) >= self._cooldown

    def record_notification(self, job: str) -> None:
        self._state.last_notified[job] = time.monotonic()
        self._state.suppressed_count.pop(job, None)

    def record_suppression(self, job: str) -> None:
        self._state.suppressed_count[job] = (
            self._state.suppressed_count.get(job, 0) + 1
        )

    # ------------------------------------------------------------------
    def notify(self, events, alert_cfg) -> Dict[str, int]:
        """Filter *events* by cooldown then dispatch.

        Returns a dict with 'sent' and 'suppressed' counts.
        """
        eligible = []
        suppressed = 0
        for ev in events:
            job = ev.job if hasattr(ev, "job") else str(ev)
            if self.should_notify(job):
                eligible.append(ev)
                self.record_notification(job)
            else:
                self.record_suppression(job)
                suppressed += 1

        if eligible:
            self._dispatch(eligible, alert_cfg)

        return {"sent": len(eligible), "suppressed": suppressed}

    def suppressed_counts(self) -> Dict[str, int]:
        return dict(self._state.suppressed_count)

    def reset(self) -> None:
        """Clear all cooldown history (useful for testing)."""
        self._state = NotifierState()
