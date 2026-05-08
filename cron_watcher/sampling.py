"""Event sampling — drop a configurable fraction of non-critical events
to reduce alert noise under high-volume conditions."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

from cron_watcher.log_parser import CronEvent


@dataclass
class SamplingConfig:
    enabled: bool = False
    # Keep this fraction of events (1.0 = keep all, 0.1 = keep 10 %)
    rate: float = 1.0
    # Jobs listed here are always kept regardless of rate
    always_include: List[str] = field(default_factory=list)


def sampling_config_from_dict(raw: dict) -> SamplingConfig:
    section = raw.get("sampling", {})
    return SamplingConfig(
        enabled=bool(section.get("enabled", False)),
        rate=float(section.get("rate", 1.0)),
        always_include=list(section.get("always_include", [])),
    )


def _is_pinned(event: CronEvent, always_include: List[str]) -> bool:
    """Return True if the event's job matches any pinned pattern."""
    import re
    for pattern in always_include:
        if re.search(pattern, event.job or ""):
            return True
    return False


def sample_events(
    events: List[CronEvent],
    cfg: SamplingConfig,
    rng: random.Random | None = None,
) -> List[CronEvent]:
    """Return a sampled subset of *events* according to *cfg*.

    Events whose job name matches an ``always_include`` pattern are
    never dropped.  All others are kept with probability ``cfg.rate``.
    """
    if not cfg.enabled or cfg.rate >= 1.0:
        return events

    _rng = rng or random.Random()
    result: List[CronEvent] = []
    for ev in events:
        if _is_pinned(ev, cfg.always_include) or _rng.random() < cfg.rate:
            result.append(ev)
    return result
