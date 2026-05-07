"""Module-level singletons for cooldown state."""
from __future__ import annotations

from typing import List, Optional

from cron_watcher.cooldown import CooldownConfig, CooldownState, cooldown_config_from_dict
from cron_watcher.log_parser import CronEvent

_config: Optional[CooldownConfig] = None
_state: Optional[CooldownState] = None


def get_cooldown_config(raw: Optional[dict] = None) -> CooldownConfig:
    global _config
    if _config is None:
        _config = cooldown_config_from_dict(raw or {})
    return _config


def get_cooldown_state() -> CooldownState:
    global _state
    if _state is None:
        _state = CooldownState()
    return _state


def reset_cooldown(raw: Optional[dict] = None) -> None:
    global _config, _state
    _config = cooldown_config_from_dict(raw or {})
    _state = CooldownState()


def filter_cooled_down(events: List[CronEvent]) -> List[CronEvent]:
    """Drop events whose job is still within the cooldown window."""
    cfg = get_cooldown_config()
    state = get_cooldown_state()
    allowed: List[CronEvent] = []
    for ev in events:
        if state.check_and_record(ev.job_name, cfg):
            allowed.append(ev)
    return allowed
