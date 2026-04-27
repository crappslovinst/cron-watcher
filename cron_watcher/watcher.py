"""Core watcher: tails a log file and emits failure events."""

import logging
import os
import time
from collections.abc import Callable
from typing import Optional

from cron_watcher.log_parser import CronEvent, parse_line

logger = logging.getLogger(__name__)


class LogWatcher:
    """Tail a cron log file and invoke a callback on each failure event."""

    def __init__(
        self,
        log_path: str,
        on_failure: Callable[[CronEvent], None],
        poll_interval: float = 1.0,
        seek_end: bool = True,
    ) -> None:
        self.log_path = log_path
        self.on_failure = on_failure
        self.poll_interval = poll_interval
        self._seek_end = seek_end
        self._running = False
        self._file = None
        self._inode: Optional[int] = None

    def _open_file(self) -> None:
        self._file = open(self.log_path, "r")
        self._inode = os.stat(self.log_path).st_ino
        if self._seek_end:
            self._file.seek(0, 2)  # seek to end
            self._seek_end = False
        logger.debug("Opened log file: %s (inode=%s)", self.log_path, self._inode)

    def _check_rotation(self) -> bool:
        """Return True if the log file has been rotated."""
        try:
            current_inode = os.stat(self.log_path).st_ino
        except FileNotFoundError:
            return True
        return current_inode != self._inode

    def _process_new_lines(self) -> None:
        if self._file is None:
            return
        for line in self._file:
            event = parse_line(line)
            if event and event.is_failure:
                logger.info("Failure detected: %s", event.message)
                try:
                    self.on_failure(event)
                except Exception:
                    logger.exception("Error in on_failure callback")

    def run_once(self) -> None:
        """Process any new lines currently available (non-blocking)."""
        if self._file is None:
            self._open_file()
        if self._check_rotation():
            logger.info("Log rotation detected, reopening file.")
            self._file.close()
            self._open_file()
        self._process_new_lines()

    def start(self) -> None:
        """Block and continuously tail the log file."""
        self._running = True
        logger.info("Starting watcher on %s", self.log_path)
        while self._running:
            self.run_once()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False
        if self._file:
            self._file.close()
            self._file = None
        logger.info("Watcher stopped.")
