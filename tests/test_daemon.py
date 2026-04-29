"""Tests for cron_watcher.daemon."""

from unittest.mock import MagicMock, call, patch

import pytest

from cron_watcher.config import AlertConfig, Config
from cron_watcher.daemon import CronWatcherDaemon
from cron_watcher.log_parser import CronEvent


@pytest.fixture()
def cfg():
    return Config(
        log_file="/var/log/syslog",
        report_interval=0,  # disable scheduler in unit tests
        top_n=5,
        alerts=[],
    )


@pytest.fixture()
def failure_event():
    return CronEvent(
        timestamp="2024-01-01T10:00:00",
        job="backup",
        command="/usr/bin/backup.sh",
        is_failure=True,
        exit_code=1,
        message="FAILED",
    )


def test_dispatch_report_clears_pending(cfg, failure_event):
    daemon = CronWatcherDaemon(cfg)
    daemon._pending = [failure_event]
    with patch("cron_watcher.daemon.build_report") as mock_build, \
         patch("cron_watcher.daemon.format_text_report", return_value="report"):
        mock_build.return_value = MagicMock()
        daemon._dispatch_report()
    assert daemon._pending == []


def test_dispatch_report_skips_when_empty(cfg):
    daemon = CronWatcherDaemon(cfg)
    with patch("cron_watcher.daemon.build_report") as mock_build:
        daemon._dispatch_report()
        mock_build.assert_not_called()


def test_scheduler_started_when_interval_nonzero():
    cfg = Config(log_file="/var/log/syslog", report_interval=60, top_n=5, alerts=[])
    daemon = CronWatcherDaemon(cfg)
    with patch.object(daemon._watcher, "start"), \
         patch.object(daemon._watcher, "stop"), \
         patch("cron_watcher.daemon.ScheduledTask") as MockTask:
        mock_task_instance = MagicMock()
        MockTask.return_value = mock_task_instance
        # Simulate immediate stop via poll_loop
        with patch.object(daemon, "_poll_loop"):
            daemon.start()
        mock_task_instance.start.assert_called_once()


def test_failures_trigger_alert_dispatch(cfg, failure_event):
    daemon = CronWatcherDaemon(cfg)
    cfg.alerts = [AlertConfig(type="webhook", url="http://example.com")]
    with patch.object(daemon._watcher, "poll", side_effect=[[failure_event], KeyboardInterrupt]), \
         patch("cron_watcher.daemon.dispatch_alerts") as mock_dispatch:
        try:
            daemon._poll_loop()
        except KeyboardInterrupt:
            pass
        mock_dispatch.assert_called_once()
        args = mock_dispatch.call_args[0]
        assert failure_event in args[0]


def test_stop_sets_running_false(cfg):
    daemon = CronWatcherDaemon(cfg)
    daemon._running = True
    with patch.object(daemon._watcher, "stop"):
        daemon.stop()
    assert daemon._running is False
