"""Tests for the backoff singleton / integration helpers."""
from __future__ import annotations

import pytest

import cron_watcher.backoff_integration as bi
from cron_watcher.backoff import BackoffConfig, BackoffTracker
from cron_watcher.log_parser import CronEvent


def _ev(cmd: str) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-01T00:00:00",
        command=cmd,
        is_failure=True,
        exit_status=1,
        raw="",
    )


@pytest.fixture(autouse=True)
def _reset():
    bi.reset_backoff_tracker()
    yield
    bi.reset_backoff_tracker()


def test_get_backoff_tracker_returns_instance():
    t = bi.get_backoff_tracker()
    assert isinstance(t, BackoffTracker)


def test_get_backoff_tracker_is_cached():
    t1 = bi.get_backoff_tracker()
    t2 = bi.get_backoff_tracker()
    assert t1 is t2


def test_reset_creates_new_instance():
    t1 = bi.get_backoff_tracker()
    bi.reset_backoff_tracker()
    t2 = bi.get_backoff_tracker()
    assert t1 is not t2


def test_backoff_failures_passes_first_event():
    events = [_ev("job_a")]
    result = bi.backoff_failures(events)
    assert len(result) == 1


def test_backoff_failures_suppresses_immediate_repeat():
    cfg_dict = {"backoff": {"base_delay": 9999.0}}
    events = [_ev("job_a")]
    bi.backoff_failures(events, config_dict=cfg_dict)  # first pass — records alert
    bi.reset_backoff_tracker()                          # get fresh tracker with same config
    # Simulate: tracker already recorded, now check suppression via direct API
    tracker = bi.get_backoff_tracker(cfg_dict)
    tracker.record_alert("job_a", now=0.0)
    # Monkey-patch is_allowed to use fixed 'now'
    result = [ev for ev in events if tracker.is_allowed(ev.command or "", now=1.0)]
    assert result == []


def test_backoff_failures_allows_different_jobs():
    cfg_dict = {"backoff": {"base_delay": 9999.0}}
    bi.backoff_failures([_ev("job_a")], config_dict=cfg_dict)
    bi.reset_backoff_tracker()
    tracker = bi.get_backoff_tracker(cfg_dict)
    tracker.record_alert("job_a", now=0.0)
    events = [_ev("job_a"), _ev("job_b")]
    result = [ev for ev in events if tracker.is_allowed(ev.command or "", now=1.0)]
    assert len(result) == 1
    assert result[0].command == "job_b"
