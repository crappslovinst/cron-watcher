"""Tests for cron_watcher.sampling_integration singleton helpers."""
from __future__ import annotations

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.sampling_integration import (
    get_sampling_config,
    reset_sampling_config,
    sampled_failures,
)


def _ev(job: str = "/usr/bin/job") -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T04:00:00",
        job=job,
        exit_status=1,
        is_failure=True,
        raw="raw",
    )


@pytest.fixture(autouse=True)
def _reset():
    reset_sampling_config()
    yield
    reset_sampling_config()


def test_get_sampling_config_returns_instance():
    cfg = get_sampling_config()
    assert cfg is not None


def test_get_sampling_config_is_cached():
    cfg1 = get_sampling_config()
    cfg2 = get_sampling_config()
    assert cfg1 is cfg2


def test_reset_creates_new_instance():
    cfg1 = get_sampling_config()
    reset_sampling_config()
    cfg2 = get_sampling_config()
    assert cfg1 is not cfg2


def test_sampled_failures_passthrough_when_disabled():
    events = [_ev(), _ev(), _ev()]
    result = sampled_failures(events, {"sampling": {"enabled": False}})
    assert result == events


def test_sampled_failures_drops_events_when_rate_zero():
    reset_sampling_config()
    events = [_ev() for _ in range(50)]
    raw = {"sampling": {"enabled": True, "rate": 0.0}}
    result = sampled_failures(events, raw)
    assert result == []


def test_sampled_failures_respects_always_include():
    reset_sampling_config()
    pinned = _ev("/usr/bin/critical-backup")
    other = _ev("/usr/bin/routine")
    raw = {
        "sampling": {
            "enabled": True,
            "rate": 0.0,
            "always_include": ["critical"],
        }
    }
    result = sampled_failures([pinned, other], raw)
    assert pinned in result
    assert other not in result
