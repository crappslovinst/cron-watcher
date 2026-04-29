"""Wire RateLimitedNotifier into the daemon's alert dispatch path."""
from __future__ import annotations

from typing import List

from cron_watcher.config import Config
from cron_watcher.log_parser import CronEvent
from cron_watcher.notifier import RateLimitedNotifier

# Module-level singleton so cooldown state persists across poll cycles.
_notifier: RateLimitedNotifier | None = None


def get_notifier(cfg: Config) -> RateLimitedNotifier:
    """Return (or create) the singleton notifier configured from *cfg*."""
    global _notifier
    if _notifier is None:
        cooldown = getattr(cfg.alert, "cooldown_seconds", 300)
        _notifier = RateLimitedNotifier(cooldown_seconds=cooldown)
    return _notifier


def dispatch_with_ratelimit(
    events: List[CronEvent],
    cfg: Config,
) -> dict:
    """Dispatch *events* through the rate-limited notifier.

    Returns the {'sent': n, 'suppressed': n} summary.
    """
    notifier = get_notifier(cfg)
    return notifier.notify(events, cfg.alert)


def reset_notifier() -> None:
    """Reset the singleton — intended for tests / daemon restart."""
    global _notifier
    _notifier = None
