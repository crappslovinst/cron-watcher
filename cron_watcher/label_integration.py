"""Singleton helpers so the rest of the daemon can share one LabelConfig instance."""
from __future__ import annotations

from typing import Dict, List, Optional

from cron_watcher.label import (
    LabelConfig,
    annotate_events,
    label_config_from_dict,
    resolve_tags,
)
from cron_watcher.log_parser import CronEvent

_label_config: Optional[LabelConfig] = None


def get_label_config(raw: Optional[dict] = None) -> LabelConfig:
    """Return (and lazily create) the shared LabelConfig.

    Pass *raw* on the first call to initialise from config; subsequent calls
    ignore *raw* and return the cached instance.
    """
    global _label_config
    if _label_config is None:
        _label_config = label_config_from_dict(raw or {})
    return _label_config


def reset_label_config() -> None:
    """Discard the cached instance (useful in tests)."""
    global _label_config
    _label_config = None


def tagged_failures(events: List[CronEvent]) -> List[Dict]:
    """Annotate *events* with tags using the shared config.

    Returns a list of dicts ready for reporting or alerting payloads.
    """
    cfg = get_label_config()
    return annotate_events(events, cfg)
