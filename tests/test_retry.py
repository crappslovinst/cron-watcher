"""Tests for cron_watcher.retry and cron_watcher.retry_integration."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from cron_watcher.retry import (
    RetryConfig,
    RetryResult,
    _compute_delay,
    with_retry,
    retry_config_from_dict,
)
from cron_watcher.retry_integration import (
    get_retry_config,
    reset_retry_config,
    dispatch_with_retry,
)


# ---------------------------------------------------------------------------
# _compute_delay
# ---------------------------------------------------------------------------

def test_compute_delay_first_attempt():
    cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=30.0)
    assert _compute_delay(0, cfg) == 1.0


def test_compute_delay_second_attempt():
    cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=30.0)
    assert _compute_delay(1, cfg) == 2.0


def test_compute_delay_capped_at_max():
    cfg = RetryConfig(base_delay=10.0, backoff_factor=4.0, max_delay=30.0)
    assert _compute_delay(5, cfg) == 30.0


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def test_success_on_first_attempt():
    fn = MagicMock(return_value="ok")
    result = with_retry(fn, RetryConfig(max_attempts=3), label="test")
    assert result.success is True
    assert result.attempts == 1
    assert result.value == "ok"
    fn.assert_called_once()


def test_success_after_transient_failure():
    fn = MagicMock(side_effect=[RuntimeError("boom"), "ok"])
    with patch("cron_watcher.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=3), label="test")
    assert result.success is True
    assert result.attempts == 2


def test_failure_exhausts_all_attempts():
    fn = MagicMock(side_effect=RuntimeError("always fails"))
    with patch("cron_watcher.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=3), label="test")
    assert result.success is False
    assert result.attempts == 3
    assert isinstance(result.last_exception, RuntimeError)
    assert fn.call_count == 3


def test_no_sleep_on_single_attempt():
    fn = MagicMock(side_effect=ValueError("nope"))
    with patch("cron_watcher.retry.time.sleep") as mock_sleep:
        with_retry(fn, RetryConfig(max_attempts=1))
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# retry_config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_empty_dict_uses_defaults():
    cfg = retry_config_from_dict({})
    assert cfg.max_attempts == 3
    assert cfg.base_delay == 1.0
    assert cfg.backoff_factor == 2.0
    assert cfg.max_delay == 30.0


def test_config_from_dict_overrides():
    cfg = retry_config_from_dict({"max_attempts": 5, "base_delay": 0.5})
    assert cfg.max_attempts == 5
    assert cfg.base_delay == 0.5


# ---------------------------------------------------------------------------
# retry_integration
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    reset_retry_config()
    yield
    reset_retry_config()


def test_get_retry_config_returns_instance():
    cfg = get_retry_config()
    assert isinstance(cfg, RetryConfig)


def test_get_retry_config_is_cached():
    a = get_retry_config()
    b = get_retry_config()
    assert a is b


def test_reset_creates_new_instance():
    a = get_retry_config()
    reset_retry_config()
    b = get_retry_config()
    assert a is not b


def test_dispatch_with_retry_success():
    fn = MagicMock(return_value=42)
    result = dispatch_with_retry(fn, label="unit-test")
    assert result.success is True
    assert result.value == 42


def test_dispatch_with_retry_uses_provided_cfg():
    fn = MagicMock(side_effect=[RuntimeError("x"), "done"])
    custom = RetryConfig(max_attempts=2, base_delay=0.0)
    with patch("cron_watcher.retry.time.sleep"):
        result = dispatch_with_retry(fn, cfg=custom)
    assert result.success is True
    assert result.attempts == 2
