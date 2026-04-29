"""Tests for cron_watcher.filter_integration."""
import pytest
from unittest.mock import MagicMock

from cron_watcher.log_parser import CronEvent
from cron_watcher.filter_integration import (
    get_filter_config,
    reset_filter_config,
    filtered_failures,
)


def _ev(command="job", exit_status=1, is_failure=True):
    return CronEvent(
        timestamp=None,
        command=command,
        exit_status=exit_status,
        is_failure=is_failure,
        raw="raw",
        extra={},
    )


@pytest.fixture(autouse=True)
def _reset():
    reset_filter_config()
    yield
    reset_filter_config()


def _cfg(filter_dict=None):
    cfg = MagicMock()
    cfg.filter = filter_dict or {}
    return cfg


def test_get_filter_config_returns_instance():
    cfg = _cfg()
    fc = get_filter_config(cfg)
    assert fc is not None


def test_get_filter_config_is_cached():
    cfg = _cfg()
    fc1 = get_filter_config(cfg)
    fc2 = get_filter_config(cfg)
    assert fc1 is fc2


def test_reset_creates_new_instance():
    cfg = _cfg()
    fc1 = get_filter_config(cfg)
    reset_filter_config()
    fc2 = get_filter_config(cfg)
    assert fc1 is not fc2


def test_filtered_failures_excludes_successes():
    events = [_ev(is_failure=True), _ev(is_failure=False, exit_status=0)]
    result = filtered_failures(events, _cfg())
    assert all(e.is_failure for e in result)


def test_filtered_failures_applies_exclude_jobs():
    events = [_ev("noisy"), _ev("important")]
    cfg = _cfg({"exclude_jobs": ["noisy"]})
    result = filtered_failures(events, cfg)
    assert len(result) == 1
    assert result[0].command == "important"


def test_filtered_failures_empty_input():
    assert filtered_failures([], _cfg()) == []
