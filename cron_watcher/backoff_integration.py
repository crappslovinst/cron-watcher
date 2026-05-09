"""Singleton helpers that wire BackoffTracker into the daemon pipeline."""
from __future__ import annotations

from typing import List, Optional

from cron_watcher.backoff import BackoffConfig, BackoffTracker, backoff_config_from_dict
from cron_watcher.log_parser import CronEvent

_tracker: Optional[BackoffTracker] = None
_config: Optional[BackoffConfig] = None


def get_backoff_tracker(config_dict: Optional[dict] = None) -> BackoffTracker:
    """Return (and lazily create) the global BackoffTracker."""
    global _tracker, _config
    if _tracker is None:
        cfg = backoff_config_from_dict(config_dict or {})
        _config = cfg
        _tracker = BackoffTracker(config=cfg)
    return _tracker


def reset_backoff_tracker() -> None:
    """Discard the singleton — useful in tests and on config reload."""
    global _tracker, _config
    _tracker = None
    _config = None


def backoff_failures(
    events: List[CronEvent],
    config_dict: Optional[dict] = None,
) -> List[CronEvent]:
    """Filter *events* to those whose job is not currently backed off.

    Side-effect: records an alert for every event that passes through.
    """
    tracker = get_backoff_tracker(config_dict)
    allowed: List[CronEvent] = []
    for ev in events:
        job = ev.command or ""
        if tracker.is_allowed(job):
            tracker.record_alert(job)
            allowed.append(ev)
    return allowed
