"""Singleton helpers that wire RetryConfig into the rest of the daemon."""

from __future__ import annotations

from typing import Callable, Any

from cron_watcher.retry import RetryConfig, RetryResult, with_retry, retry_config_from_dict

_retry_cfg: RetryConfig | None = None


def get_retry_config(raw: dict | None = None) -> RetryConfig:
    """Return the process-level RetryConfig, creating it once from *raw* if needed."""
    global _retry_cfg
    if _retry_cfg is None:
        _retry_cfg = retry_config_from_dict(raw or {})
    return _retry_cfg


def reset_retry_config() -> None:
    """Discard the cached config (useful in tests)."""
    global _retry_cfg
    _retry_cfg = None


def dispatch_with_retry(
    fn: Callable[[], Any],
    *,
    label: str = "alert dispatch",
    cfg: RetryConfig | None = None,
) -> RetryResult:
    """Dispatch *fn* using the global retry config (or *cfg* if provided)."""
    effective_cfg = cfg if cfg is not None else get_retry_config()
    return with_retry(fn, effective_cfg, label=label)
