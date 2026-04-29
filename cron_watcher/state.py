"""Persistent state store for cron-watcher (last-seen inode, offset, run counts)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WatcherState:
    log_path: str = ""
    inode: int = 0
    offset: int = 0
    last_event_ts: Optional[str] = None
    total_events_seen: int = 0
    total_failures_seen: int = 0
    extra: dict = field(default_factory=dict)


def load_state(path: str) -> WatcherState:
    """Load state from *path*; return a fresh WatcherState if the file is
    missing or corrupt."""
    if not os.path.exists(path):
        logger.debug("State file %s not found, starting fresh.", path)
        return WatcherState()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return WatcherState(
            log_path=data.get("log_path", ""),
            inode=int(data.get("inode", 0)),
            offset=int(data.get("offset", 0)),
            last_event_ts=data.get("last_event_ts"),
            total_events_seen=int(data.get("total_events_seen", 0)),
            total_failures_seen=int(data.get("total_failures_seen", 0)),
            extra=data.get("extra", {}),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("Could not parse state file %s: %s — resetting.", path, exc)
        return WatcherState()


def save_state(path: str, state: WatcherState) -> None:
    """Atomically write *state* to *path*."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(asdict(state), fh, indent=2)
        os.replace(tmp, path)
        logger.debug("State saved to %s.", path)
    except OSError as exc:
        logger.error("Failed to save state to %s: %s", path, exc)
        try:
            os.unlink(tmp)
        except OSError:
            pass
