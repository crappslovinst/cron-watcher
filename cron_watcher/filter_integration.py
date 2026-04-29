"""Wires FilterConfig into the daemon pipeline."""
from __future__ import annotations

from typing import List, Sequence

from cron_watcher.config import Config
from cron_watcher.filter import FilterConfig, apply_filters, filter_config_from_dict
from cron_watcher.log_parser import CronEvent

_filter_cfg: FilterConfig | None = None


def get_filter_config(cfg: Config) -> FilterConfig:
    """Build (and cache) a FilterConfig from the application Config."""
    global _filter_cfg
    if _filter_cfg is None:
        raw = getattr(cfg, "filter", None) or {}
        _filter_cfg = filter_config_from_dict(raw if isinstance(raw, dict) else {})
    return _filter_cfg


def reset_filter_config() -> None:
    """Reset cached instance (useful in tests)."""
    global _filter_cfg
    _filter_cfg = None


def filtered_failures(
    events: Sequence[CronEvent], cfg: Config
) -> List[CronEvent]:
    """Return only failure events that pass the active filter configuration."""
    failures = [e for e in events if e.is_failure]
    return apply_filters(failures, get_filter_config(cfg))
