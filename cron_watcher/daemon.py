"""Main daemon entry-point: wires together watcher, alerter, and scheduler."""

import logging
import signal
import sys
from types import FrameType
from typing import List, Optional

from cron_watcher.alerter import dispatch_alerts
from cron_watcher.config import Config, load_config
from cron_watcher.log_parser import CronEvent, filter_failures
from cron_watcher.reporter import build_report, format_text_report
from cron_watcher.scheduler import ScheduledTask
from cron_watcher.watcher import LogWatcher

logger = logging.getLogger(__name__)


class CronWatcherDaemon:
    """Orchestrates log watching, failure alerting, and scheduled reporting."""

    def __init__(self, config: Config):
        self.config = config
        self._watcher = LogWatcher(config.log_file)
        self._pending: List[CronEvent] = []
        self._scheduler: Optional[ScheduledTask] = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the daemon; blocks until a stop signal is received."""
        logger.info("cron-watcher daemon starting.")
        self._running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._watcher.start()

        if self.config.report_interval > 0:
            self._scheduler = ScheduledTask(
                interval_seconds=self.config.report_interval,
                task=self._dispatch_report,
                name="report-scheduler",
            )
            self._scheduler.start()

        self._poll_loop()

    def stop(self) -> None:
        """Stop the daemon, watcher, and any scheduled tasks."""
        logger.info("cron-watcher daemon stopping.")
        self._running = False
        self._watcher.stop()
        if self._scheduler:
            self._scheduler.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Continuously poll the log watcher and dispatch alerts for failures."""
        while self._running:
            try:
                events = self._watcher.poll()
            except Exception:
                logger.exception("Unexpected error while polling log watcher; continuing.")
                continue
            failures = filter_failures(events)
            if failures:
                self._pending.extend(failures)
                if self.config.alerts:
                    try:
                        dispatch_alerts(failures, self.config.alerts)
                    except Exception:
                        logger.exception("Failed to dispatch alerts for %d failure(s).", len(failures))

    def _dispatch_report(self) -> None:
        """Build and log a periodic summary report of pending failure events."""
        if not self._pending:
            logger.debug("No pending events; skipping report dispatch.")
            return
        report = build_report(self._pending, top_n=self.config.top_n)
        text = format_text_report(report)
        logger.info("Periodic report:\n%s", text)
        self._pending.clear()

    def _handle_signal(self, signum: int, frame: Optional[FrameType]) -> None:
        logger.info("Received signal %d — shutting down.", signum)
        self.stop()
        sys.exit(0)


def run_daemon(config_path: str) -> None:
    """Load config from *config_path* and run the daemon until interrupted."""
    config = load_config(config_path)
    daemon = CronWatcherDaemon(config)
    daemon.start()
