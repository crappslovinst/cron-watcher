"""Scheduled report generation and periodic alert dispatch."""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Runs a callable on a fixed interval in a background thread."""

    def __init__(self, interval_seconds: int, task: Callable, name: str = "task"):
        self.interval = interval_seconds
        self.task = task
        self.name = name
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.error_count: int = 0

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Task '%s' is already running.", self.name)
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=self.name)
        self._thread.start()
        logger.info("Scheduled task '%s' started (interval=%ds).", self.name, self.interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the task to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("Scheduled task '%s' stopped.", self.name)

    def _loop(self) -> None:
        next_run = time.monotonic() + self.interval
        while not self._stop_event.is_set():
            remaining = next_run - time.monotonic()
            if remaining > 0:
                self._stop_event.wait(timeout=remaining)
                continue
            self._run_once()
            next_run = time.monotonic() + self.interval

    def _run_once(self) -> None:
        try:
            self.task()
            self.last_run = datetime.utcnow()
            self.run_count += 1
            logger.debug("Task '%s' completed (run #%d).", self.name, self.run_count)
        except Exception as exc:  # noqa: BLE001
            self.error_count += 1
            logger.error("Task '%s' raised an error: %s", self.name, exc)

    @property
    def next_run_in(self) -> Optional[timedelta]:
        """Approximate time until next execution (best-effort)."""
        if self.last_run is None:
            return None
        return self.last_run + timedelta(seconds=self.interval) - datetime.utcnow()

    def status(self) -> dict:
        return {
            "name": self.name,
            "interval_seconds": self.interval,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "alive": self._thread.is_alive() if self._thread else False,
        }
