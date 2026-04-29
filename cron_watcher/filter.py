"""Event filtering: suppress noise by job name, exit code, or time window."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from cron_watcher.log_parser import CronEvent


@dataclass
class FilterConfig:
    exclude_jobs: List[str] = field(default_factory=list)   # glob/regex patterns
    exclude_exit_codes: List[int] = field(default_factory=list)
    only_jobs: List[str] = field(default_factory=list)      # whitelist
    min_duration_seconds: Optional[float] = None


def _matches_any(value: str, patterns: Sequence[str]) -> bool:
    return any(re.search(p, value) for p in patterns)


def apply_filters(events: Sequence[CronEvent], cfg: FilterConfig) -> List[CronEvent]:
    """Return a filtered copy of *events* according to *cfg*."""
    result: List[CronEvent] = []
    for ev in events:
        job = ev.command or ""

        # whitelist check
        if cfg.only_jobs and not _matches_any(job, cfg.only_jobs):
            continue

        # blacklist check
        if cfg.exclude_jobs and _matches_any(job, cfg.exclude_jobs):
            continue

        # exit-code filter
        if ev.exit_status is not None and ev.exit_status in cfg.exclude_exit_codes:
            continue

        # duration filter
        if cfg.min_duration_seconds is not None:
            dur = ev.extra.get("duration") if ev.extra else None
            if dur is None or float(dur) < cfg.min_duration_seconds:
                continue

        result.append(ev)
    return result


def filter_config_from_dict(raw: dict) -> FilterConfig:
    return FilterConfig(
        exclude_jobs=raw.get("exclude_jobs", []),
        exclude_exit_codes=[int(c) for c in raw.get("exclude_exit_codes", [])],
        only_jobs=raw.get("only_jobs", []),
        min_duration_seconds=raw.get("min_duration_seconds"),
    )
