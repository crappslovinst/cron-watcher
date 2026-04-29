"""In-memory metrics collector for cron-watcher runtime stats."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Metrics:
    started_at: float = field(default_factory=time.time)
    events_processed: int = 0
    failures_detected: int = 0
    alerts_sent: int = 0
    alert_errors: int = 0
    last_alert_at: float | None = None
    log_rotations: int = 0

    def to_dict(self) -> Dict:
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "events_processed": self.events_processed,
            "failures_detected": self.failures_detected,
            "alerts_sent": self.alerts_sent,
            "alert_errors": self.alert_errors,
            "last_alert_at": self.last_alert_at,
            "log_rotations": self.log_rotations,
        }


class MetricsCollector:
    """Thread-safe singleton-style metrics store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics = Metrics()

    def reset(self) -> None:
        with self._lock:
            self._metrics = Metrics()

    def inc_events(self, n: int = 1) -> None:
        with self._lock:
            self._metrics.events_processed += n

    def inc_failures(self, n: int = 1) -> None:
        with self._lock:
            self._metrics.failures_detected += n

    def inc_alerts_sent(self, n: int = 1) -> None:
        with self._lock:
            self._metrics.alerts_sent += n
            self._metrics.last_alert_at = time.time()

    def inc_alert_errors(self, n: int = 1) -> None:
        with self._lock:
            self._metrics.alert_errors += n

    def inc_log_rotations(self, n: int = 1) -> None:
        with self._lock:
            self._metrics.log_rotations += n

    def snapshot(self) -> Dict:
        with self._lock:
            return self._metrics.to_dict()


# Module-level default collector instance
collector = MetricsCollector()
