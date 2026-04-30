"""Deduplication of cron events to avoid alerting on the same failure repeatedly."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List

from cron_watcher.log_parser import CronEvent


@dataclass
class DedupState:
    # Maps event fingerprint -> last seen timestamp
    seen: Dict[str, float] = field(default_factory=dict)


def _fingerprint(event: CronEvent) -> str:
    """Return a stable hash identifying the (job, exit_status) pair."""
    raw = f"{event.job_name}:{event.exit_status}"
    return hashlib.sha1(raw.encode()).hexdigest()


def deduplicate(
    events: List[CronEvent],
    state: DedupState,
    window_seconds: float = 300.0,
    now: float | None = None,
) -> List[CronEvent]:
    """Return only events that have not been seen within *window_seconds*.

    Side-effect: updates *state* with the fingerprints of returned events.
    """
    if now is None:
        now = time.time()

    unique: List[CronEvent] = []
    for ev in events:
        fp = _fingerprint(ev)
        last = state.seen.get(fp)
        if last is None or (now - last) >= window_seconds:
            unique.append(ev)
            state.seen[fp] = now

    return unique


def evict_expired(state: DedupState, window_seconds: float = 300.0, now: float | None = None) -> None:
    """Remove stale fingerprints from *state* to keep memory bounded."""
    if now is None:
        now = time.time()
    cutoff = now - window_seconds
    expired = [fp for fp, ts in state.seen.items() if ts < cutoff]
    for fp in expired:
        del state.seen[fp]
