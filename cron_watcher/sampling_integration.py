"""Singleton helpers so the rest of the daemon can call
``sampled_failures(events)`` without worrying about config wiring."""
from __future__ import annotations

from typing import List

from cron_watcher.log_parser import CronEvent
from cron_watcher.sampling import SamplingConfig, sample_events, sampling_config_from_dict

_config: SamplingConfig | None = None


def get_sampling_config(raw: dict | None = None) -> SamplingConfig:
    """Return the cached :class:`SamplingConfig`, creating it on first call."""
    global _config
    if _config is None:
        _config = sampling_config_from_dict(raw or {})
    return _config


def reset_sampling_config() -> None:
    """Discard the cached config (useful in tests)."""
    global _config
    _config = None


def sampled_failures(
    events: List[CronEvent],
    raw_cfg: dict | None = None,
) -> List[CronEvent]:
    """Apply sampling to *events* using the singleton config."""
    cfg = get_sampling_config(raw_cfg)
    return sample_events(events, cfg)
