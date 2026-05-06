"""Module-level singleton helpers for silence windows."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from cron_watcher.log_parser import CronEvent
from cron_watcher.silence import SilenceWindow, filter_silenced, silence_config_from_dict

_windows: Optional[List[SilenceWindow]] = None


def get_silence_windows(raw: Optional[list] = None) -> List[SilenceWindow]:
    """Return the cached silence windows, initialising from *raw* on first call."""
    global _windows
    if _windows is None:
        _windows = silence_config_from_dict(raw or [])
    return _windows


def reset_silence_windows() -> None:
    """Drop the cached windows (useful in tests and config reloads)."""
    global _windows
    _windows = None


def apply_silence(
    events: List[CronEvent],
    now: Optional[datetime] = None,
) -> List[CronEvent]:
    """Filter *events* through the globally configured silence windows."""
    windows = get_silence_windows()
    return filter_silenced(events, windows, now)
