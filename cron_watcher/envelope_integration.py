"""Singleton helpers so the rest of the daemon uses one EnvelopeConfig."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from cron_watcher.envelope import EnvelopeConfig, envelope_config_from_dict, wrap
from cron_watcher.log_parser import CronEvent

_config: Optional[EnvelopeConfig] = None


def get_envelope_config(raw: Optional[Dict[str, Any]] = None) -> EnvelopeConfig:
    """Return the cached EnvelopeConfig, initialising from *raw* if needed."""
    global _config
    if _config is None:
        _config = envelope_config_from_dict(raw or {})
    return _config


def reset_envelope_config() -> None:
    """Discard the cached instance (useful for tests)."""
    global _config
    _config = None


def wrapped_failures(
    events: List[CronEvent],
    raw_cfg: Optional[Dict[str, Any]] = None,
) -> Dict:
    """Convenience: wrap *events* using the singleton config."""
    cfg = get_envelope_config(raw_cfg)
    return wrap(events, cfg)
