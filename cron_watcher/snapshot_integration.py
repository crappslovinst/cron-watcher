"""Wires snapshot writing into the daemon via the global config + metrics."""

from __future__ import annotations

from typing import Optional

from cron_watcher.snapshot import SnapshotConfig, snapshot_config_from_dict, write_snapshot

_cfg: Optional[SnapshotConfig] = None


def get_snapshot_config(raw: Optional[dict] = None) -> SnapshotConfig:
    """Return (and cache) a SnapshotConfig built from *raw* dict."""
    global _cfg
    if _cfg is None:
        _cfg = snapshot_config_from_dict(raw or {})
    return _cfg


def reset_snapshot_config() -> None:
    """Drop the cached config (useful in tests)."""
    global _cfg
    _cfg = None


def do_snapshot(extra: Optional[dict] = None) -> bool:
    """Collect live data and write the snapshot file.

    Imports are deferred so that the module stays importable even when the
    full daemon stack is not running (e.g. during unit tests).
    """
    from cron_watcher.metrics import MetricsCollector  # local import
    from cron_watcher.state_integration import get_state_path  # local import
    from cron_watcher.state import load_state  # local import

    cfg = get_snapshot_config()
    if not cfg.enabled:
        return False

    def _metrics() -> dict:
        try:
            return MetricsCollector.instance().snapshot().to_dict()
        except Exception:
            return {}

    def _state() -> dict:
        try:
            return load_state(get_state_path()).__dict__
        except Exception:
            return {}

    return write_snapshot(cfg, _metrics, _state, extra=extra)
