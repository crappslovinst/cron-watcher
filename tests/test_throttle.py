"""Tests for cron_watcher.throttle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cron_watcher.throttle import AlertThrottle, ThrottleConfig, throttle_config_from_dict


@pytest.fixture()
def throttle() -> AlertThrottle:
    return AlertThrottle(ThrottleConfig(window_seconds=60, max_alerts_per_window=2))


def test_first_alert_is_allowed(throttle: AlertThrottle) -> None:
    assert throttle.should_send("backup") is True


def test_alert_allowed_up_to_limit(throttle: AlertThrottle) -> None:
    for _ in range(2):
        assert throttle.should_send("backup") is True
        throttle.record("backup")


def test_alert_suppressed_over_limit(throttle: AlertThrottle) -> None:
    for _ in range(2):
        throttle.record("backup")
    assert throttle.should_send("backup") is False


def test_remaining_decrements(throttle: AlertThrottle) -> None:
    assert throttle.remaining("backup") == 2
    throttle.record("backup")
    assert throttle.remaining("backup") == 1
    throttle.record("backup")
    assert throttle.remaining("backup") == 0


def test_remaining_never_negative(throttle: AlertThrottle) -> None:
    for _ in range(5):
        throttle.record("backup")
    assert throttle.remaining("backup") == 0


def test_window_resets_after_expiry(throttle: AlertThrottle) -> None:
    throttle.record("backup")
    throttle.record("backup")
    assert throttle.should_send("backup") is False

    future = time.monotonic() + 61
    with patch("time.monotonic", return_value=future):
        assert throttle.should_send("backup") is True


def test_different_jobs_are_independent(throttle: AlertThrottle) -> None:
    throttle.record("backup")
    throttle.record("backup")
    assert throttle.should_send("cleanup") is True


def test_reset_single_job(throttle: AlertThrottle) -> None:
    throttle.record("backup")
    throttle.record("backup")
    throttle.reset("backup")
    assert throttle.should_send("backup") is True


def test_reset_all_jobs(throttle: AlertThrottle) -> None:
    throttle.record("backup")
    throttle.record("cleanup")
    throttle.reset()
    assert throttle.should_send("backup") is True
    assert throttle.should_send("cleanup") is True


def test_throttle_config_from_dict() -> None:
    cfg = throttle_config_from_dict({"window_seconds": "120", "max_alerts_per_window": "5"})
    assert cfg.window_seconds == 120
    assert cfg.max_alerts_per_window == 5


def test_throttle_config_defaults() -> None:
    cfg = throttle_config_from_dict({})
    assert cfg.window_seconds == 300
    assert cfg.max_alerts_per_window == 3
