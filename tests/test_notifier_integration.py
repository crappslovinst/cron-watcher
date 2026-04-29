"""Integration tests for notifier_integration module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import cron_watcher.notifier_integration as ni
from cron_watcher.log_parser import CronEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    """Ensure the module-level singleton is cleared between tests."""
    ni.reset_notifier()
    yield
    ni.reset_notifier()


@pytest.fixture
def cfg():
    alert = MagicMock()
    alert.cooldown_seconds = 10
    config = MagicMock()
    config.alert = alert
    return config


def _ev(job: str = "backup") -> CronEvent:
    return CronEvent(
        timestamp="2024-06-01T12:00:00",
        job=job,
        pid=42,
        message="CMD failed",
        is_failure=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_notifier_returns_same_instance(cfg):
    n1 = ni.get_notifier(cfg)
    n2 = ni.get_notifier(cfg)
    assert n1 is n2


def test_reset_notifier_creates_new_instance(cfg):
    n1 = ni.get_notifier(cfg)
    ni.reset_notifier()
    n2 = ni.get_notifier(cfg)
    assert n1 is not n2


def test_dispatch_with_ratelimit_sends_events(cfg):
    with patch("cron_watcher.notifier.dispatch_alerts") as mock_da:
        ni.reset_notifier()
        result = ni.dispatch_with_ratelimit([_ev()], cfg)
    assert result["sent"] == 1
    assert result["suppressed"] == 0
    mock_da.assert_called_once()


def test_dispatch_suppresses_duplicate_within_cooldown(cfg):
    with patch("cron_watcher.notifier.dispatch_alerts") as mock_da:
        ni.reset_notifier()
        ni.dispatch_with_ratelimit([_ev("job_x")], cfg)
        result = ni.dispatch_with_ratelimit([_ev("job_x")], cfg)
    assert result["suppressed"] == 1
    assert mock_da.call_count == 1


def test_dispatch_empty_list_does_nothing(cfg):
    with patch("cron_watcher.notifier.dispatch_alerts") as mock_da:
        ni.reset_notifier()
        result = ni.dispatch_with_ratelimit([], cfg)
    assert result["sent"] == 0
    mock_da.assert_not_called()


def test_cooldown_taken_from_config(cfg):
    cfg.alert.cooldown_seconds = 9999
    notifier = ni.get_notifier(cfg)
    assert notifier._cooldown == 9999
