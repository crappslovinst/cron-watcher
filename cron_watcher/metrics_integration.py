"""Wires MetricsCollector into the daemon's event processing pipeline.

Provides helper functions used by CronWatcherDaemon to record metrics
without coupling the daemon directly to the metrics module.
"""

from __future__ import annotations

from typing import List

from cron_watcher.log_parser import CronEvent
from cron_watcher.metrics import MetricsCollector


def record_events(
    events: List[CronEvent],
    collector: MetricsCollector,
) -> None:
    """Update counters after a batch of events has been parsed."""
    if not events:
        return
    collector.inc_events(len(events))
    failures = sum(1 for e in events if e.is_failure)
    if failures:
        collector.inc_failures(failures)


def record_alert_outcome(
    success: bool,
    collector: MetricsCollector,
    count: int = 1,
) -> None:
    """Record the outcome of an alert dispatch attempt."""
    if success:
        collector.inc_alerts_sent(count)
    else:
        collector.inc_alert_errors(count)


def record_log_rotation(collector: MetricsCollector) -> None:
    """Increment the log-rotation counter."""
    collector.inc_log_rotations()
