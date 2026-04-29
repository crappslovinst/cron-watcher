"""Tests for cron_watcher.notifier."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cron_watcher.notifier import RateLimitedNotifier
from cron_watcher.log_parser import CronEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(job: str, failure: bool = True) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-01T00:00:00",
        job=job,
        pid=1,
        message="error",
        is_failure=failure,
    )


@pytest.fixture
def mock_dispatch():
    return MagicMock()


@pytest.fixture
def notifier(mock_dispatch):
    return RateLimitedNotifier(cooldown_seconds=60, dispatch_fn=mock_dispatch)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_first_notification_is_sent(notifier, mock_dispatch, alert_cfg=None):
    ev = _event("backup")
    result = notifier.notify([ev], object())
    assert result["sent"] == 1
    assert result["suppressed"] == 0
    mock_dispatch.assert_called_once()


def test_second_notification_suppressed_within_cooldown(notifier, mock_dispatch):
    ev = _event("backup")
    cfg = object()
    notifier.notify([ev], cfg)
    result = notifier.notify([ev], cfg)
    assert result["suppressed"] == 1
    assert result["sent"] == 0
    assert mock_dispatch.call_count == 1


def test_notification_allowed_after_cooldown(mock_dispatch):
    notifier = RateLimitedNotifier(cooldown_seconds=0, dispatch_fn=mock_dispatch)
    ev = _event("cleanup")
    cfg = object()
    notifier.notify([ev], cfg)
    time.sleep(0.01)
    result = notifier.notify([ev], cfg)
    assert result["sent"] == 1
    assert mock_dispatch.call_count == 2


def test_different_jobs_notified_independently(notifier, mock_dispatch):
    cfg = object()
    result = notifier.notify([_event("job_a"), _event("job_b")], cfg)
    assert result["sent"] == 2
    assert result["suppressed"] == 0


def test_suppressed_counts_tracked(notifier, mock_dispatch):
    ev = _event("db_backup")
    cfg = object()
    notifier.notify([ev], cfg)
    notifier.notify([ev], cfg)
    notifier.notify([ev], cfg)
    counts = notifier.suppressed_counts()
    assert counts["db_backup"] == 2


def test_reset_clears_history(notifier, mock_dispatch):
    ev = _event("report")
    cfg = object()
    notifier.notify([ev], cfg)
    notifier.reset()
    assert notifier.should_notify("report") is True
    assert notifier.suppressed_counts() == {}


def test_empty_events_does_not_dispatch(notifier, mock_dispatch):
    result = notifier.notify([], object())
    assert result["sent"] == 0
    mock_dispatch.assert_not_called()


def test_uses_default_dispatch_when_none_given():
    """Constructor should import dispatch_alerts automatically."""
    with patch("cron_watcher.notifier.dispatch_alerts") as mock_da:
        n = RateLimitedNotifier(cooldown_seconds=300)
        n.notify([_event("x")], object())
        mock_da.assert_called_once()
