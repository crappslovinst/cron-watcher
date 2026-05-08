"""Tests for cron_watcher.scheduler."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cron_watcher.scheduler import ScheduledTask


@pytest.fixture()
def fast_task():
    mock = MagicMock()
    task = ScheduledTask(interval_seconds=1, task=mock, name="test-task")
    yield task, mock
    task.stop(timeout=2)


def test_task_runs_after_interval(fast_task):
    task, mock = fast_task
    task.start()
    time.sleep(1.6)
    assert mock.call_count >= 1


def test_task_increments_run_count(fast_task):
    task, mock = fast_task
    task.start()
    time.sleep(1.6)
    assert task.run_count >= 1


def test_task_sets_last_run(fast_task):
    task, mock = fast_task
    assert task.last_run is None
    task.start()
    time.sleep(1.6)
    assert task.last_run is not None


def test_task_stops_cleanly(fast_task):
    task, mock = fast_task
    task.start()
    time.sleep(0.2)
    task.stop(timeout=2)
    assert not task._thread.is_alive()


def test_double_start_is_safe(fast_task):
    task, _ = fast_task
    task.start()
    time.sleep(0.1)
    task.start()  # should log warning, not crash
    assert task._thread.is_alive()


def test_error_in_task_increments_error_count():
    def bad_task():
        raise RuntimeError("boom")

    task = ScheduledTask(interval_seconds=1, task=bad_task, name="bad")
    task.start()
    time.sleep(1.6)
    task.stop(timeout=2)
    assert task.error_count >= 1
    assert task.run_count == 0


def test_status_returns_dict(fast_task):
    task, _ = fast_task
    task.start()
    time.sleep(1.2)
    s = task.status()
    assert s["name"] == "test-task"
    assert s["interval_seconds"] == 1
    assert s["alive"] is True
    assert s["run_count"] >= 1


def test_next_run_in_none_before_first_run():
    task = ScheduledTask(interval_seconds=60, task=lambda: None, name="idle")
    assert task.next_run_in is None


def test_next_run_in_after_first_run():
    """next_run_in should be a positive float shortly after the task has run once."""
    task = ScheduledTask(interval_seconds=60, task=lambda: None, name="timing")
    task.start()
    # wait long enough for the task to fire at least once
    time.sleep(1.5)
    nri = task.next_run_in
    task.stop(timeout=2)
    assert nri is not None
    assert 0 < nri <= 60
