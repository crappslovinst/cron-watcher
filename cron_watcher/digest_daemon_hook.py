"""Hook that wires the digest feature into the daemon poll loop.

Call `maybe_dispatch_digest` at the end of each poll cycle.  When the
digest timer fires it pulls buffered failures, builds a report and
dispatches alerts exactly like the normal failure path.
"""
from __future__ import annotations

from typing import Callable, List

from cron_watcher.log_parser import CronEvent
from cron_watcher.digest_integration import accumulate, try_flush
from cron_watcher.reporter import build_report, format_text_report
from cron_watcher.alerter import dispatch_alerts
from cron_watcher.config import AlertConfig


def feed_failures(events: List[CronEvent]) -> None:
    """Buffer failure events into the digest.  Call after each poll."""
    failures = [e for e in events if e.is_failure]
    if failures:
        accumulate(failures)


def maybe_dispatch_digest(
    alert_cfg: AlertConfig,
    top_n: int = 5,
    _dispatch: Callable = dispatch_alerts,
) -> bool:
    """Flush and dispatch digest if it is due.  Returns True when sent."""
    events = try_flush()
    if not events:
        return False

    report = build_report(events, top_n=top_n)
    text = format_text_report(report)
    _dispatch(events, alert_cfg, summary=text)
    return True
