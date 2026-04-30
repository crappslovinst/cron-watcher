"""Process-level singleton for the deduplication state."""

from __future__ import annotations

from typing import List, Optional

from cron_watcher.dedup import DedupState, deduplicate, evict_expired
from cron_watcher.log_parser import CronEvent

_state: Optional[DedupState] = None


def get_dedup_state() -> DedupState:
    """Return the shared DedupState, creating it on first call."""
    global _state
    if _state is None:
        _state = DedupState()
    return _state


def reset_dedup_state() -> None:
    """Discard the shared state (useful for tests and daemon restarts)."""
    global _state
    _state = None


def dedup_failures(
    events: List[CronEvent],
    window_seconds: float = 300.0,
) -> List[CronEvent]:
    """Deduplicate *events* using the shared state.

    Also evicts expired fingerprints to keep memory usage bounded.
    """
    state = get_dedup_state()
    evict_expired(state, window_seconds=window_seconds)
    return deduplicate(events, state, window_seconds=window_seconds)
