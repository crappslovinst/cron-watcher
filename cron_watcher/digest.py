"""Periodic digest: batch multiple failure events into a single summary alert."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from cron_watcher.log_parser import CronEvent


@dataclass
class DigestConfig:
    enabled: bool = False
    interval_seconds: int = 3600  # how often to flush the digest
    min_failures: int = 1         # minimum failures before sending


@dataclass
class DigestState:
    pending: List[CronEvent] = field(default_factory=list)
    last_flush: float = field(default_factory=time.time)

    def add(self, event: CronEvent) -> None:
        self.pending.append(event)

    def should_flush(self, cfg: DigestConfig, now: Optional[float] = None) -> bool:
        if not cfg.enabled:
            return False
        now = now if now is not None else time.time()
        elapsed = now - self.last_flush
        return elapsed >= cfg.interval_seconds and len(self.pending) >= cfg.min_failures

    def flush(self, now: Optional[float] = None) -> List[CronEvent]:
        """Return pending events and reset state."""
        events = list(self.pending)
        self.pending.clear()
        self.last_flush = now if now is not None else time.time()
        return events


def digest_config_from_dict(raw: dict) -> DigestConfig:
    return DigestConfig(
        enabled=bool(raw.get("enabled", False)),
        interval_seconds=int(raw.get("interval_seconds", 3600)),
        min_failures=int(raw.get("min_failures", 1)),
    )
