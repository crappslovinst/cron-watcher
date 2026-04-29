"""Helpers that wire WatcherState into the live daemon loop.

Called by CronWatcherDaemon to persist file position across restarts and
update running counters after each poll cycle.
"""

from __future__ import annotations

import logging
import os
from typing import List

from cron_watcher.log_parser import CronEvent
from cron_watcher.state import WatcherState, load_state, save_state

logger = logging.getLogger(__name__)

_DEFAULT_STATE_PATH = "/var/lib/cron-watcher/state.json"


def get_state_path(cfg_extra: dict | None = None) -> str:
    """Return the state file path from env > config > default."""
    env = os.environ.get("CRON_WATCHER_STATE_PATH")
    if env:
        return env
    if cfg_extra and "state_path" in cfg_extra:
        return cfg_extra["state_path"]
    return _DEFAULT_STATE_PATH


def restore_offset(state_path: str, log_path: str) -> tuple[int, int]:
    """Return (inode, offset) to resume from, or (0, 0) if log rotated."""
    state = load_state(state_path)
    if not log_path or state.log_path != log_path:
        return 0, 0
    try:
        current_inode = os.stat(log_path).st_ino
    except FileNotFoundError:
        return 0, 0
    if current_inode != state.inode:
        logger.info("Log file rotated (inode changed); resetting offset.")
        return current_inode, 0
    return state.inode, state.offset


def persist_after_poll(
    state_path: str,
    log_path: str,
    inode: int,
    offset: int,
    new_events: List[CronEvent],
) -> None:
    """Update counters and flush state to disk after a poll cycle."""
    state = load_state(state_path)
    state.log_path = log_path
    state.inode = inode
    state.offset = offset
    state.total_events_seen += len(new_events)
    failures = [e for e in new_events if e.is_failure]
    state.total_failures_seen += len(failures)
    if new_events:
        last_ts = new_events[-1].timestamp
        if last_ts:
            state.last_event_ts = last_ts.isoformat() if hasattr(last_ts, "isoformat") else str(last_ts)
    save_state(state_path, state)
