"""Module-level singleton wiring for the digest feature."""
from __future__ import annotations

from typing import List, Optional

from cron_watcher.digest import DigestConfig, DigestState, digest_config_from_dict
from cron_watcher.log_parser import CronEvent

_state: Optional[DigestState] = None
_config: Optional[DigestConfig] = None


def get_digest_config(raw: Optional[dict] = None) -> DigestConfig:
    global _config
    if _config is None:
        _config = digest_config_from_dict(raw or {})
    return _config


def get_digest_state() -> DigestState:
    global _state
    if _state is None:
        _state = DigestState()
    return _state


def reset_digest(raw: Optional[dict] = None) -> None:
    global _state, _config
    _config = digest_config_from_dict(raw or {})
    _state = DigestState()


def accumulate(events: List[CronEvent]) -> None:
    """Add failure events to the digest buffer."""
    state = get_digest_state()
    for ev in events:
        state.add(ev)


def try_flush() -> List[CronEvent]:
    """Return buffered events if it is time to flush, else empty list."""
    cfg = get_digest_config()
    state = get_digest_state()
    if state.should_flush(cfg):
        return state.flush()
    return []
