"""Silence windows — suppress alerts for specific jobs during scheduled maintenance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional

from cron_watcher.log_parser import CronEvent


@dataclass
class SilenceWindow:
    """A time window during which alerts for matching jobs are suppressed."""

    pattern: str
    start: time
    end: time
    days: List[int] = field(default_factory=list)  # 0=Mon … 6=Sun; empty = every day
    _regex: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._regex = re.compile(self.pattern)

    def matches_job(self, job: str) -> bool:
        return bool(self._regex and self._regex.search(job))

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        if self.days and now.weekday() not in self.days:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # overnight window e.g. 23:00 – 01:00
        return current >= self.start or current <= self.end


def silence_config_from_dict(raw: list) -> List[SilenceWindow]:
    """Build a list of SilenceWindows from the parsed TOML/YAML config list."""
    windows: List[SilenceWindow] = []
    for entry in raw:
        start_h, start_m = map(int, entry["start"].split(":"))
        end_h, end_m = map(int, entry["end"].split(":"))
        windows.append(
            SilenceWindow(
                pattern=entry["pattern"],
                start=time(start_h, start_m),
                end=time(end_h, end_m),
                days=entry.get("days", []),
            )
        )
    return windows


def is_silenced(
    event: CronEvent,
    windows: List[SilenceWindow],
    now: Optional[datetime] = None,
) -> bool:
    """Return True if *event* falls inside any active silence window."""
    job = event.command or ""
    return any(w.matches_job(job) and w.is_active(now) for w in windows)


def filter_silenced(
    events: List[CronEvent],
    windows: List[SilenceWindow],
    now: Optional[datetime] = None,
) -> List[CronEvent]:
    """Return only events that are NOT currently silenced."""
    return [e for e in events if not is_silenced(e, windows, now)]
