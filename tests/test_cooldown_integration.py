"""Tests for cron_watcher/cooldown_integration.py"""
import time
import pytest
from cron_watcher.log_parser import CronEvent
import cron_watcher.cooldown_integration as ci


def _ev(job: str = "daily_backup") -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T02:00:00",
        job_name=job,
        command=f"/usr/bin/{job}",
        exit_status=1,
        is_failure=True,
        raw_line=f"CRON[1]: ({job}) CMD ({job})",
    )


@pytest.fixture(autouse=True)
def _reset():
    ci.reset_cooldown({"cooldown": {"enabled": True, "period": 60}})
    yield
    ci.reset_cooldown()


def test_get_cooldown_config_returns_instance():
    cfg = ci.get_cooldown_config()
    assert cfg.period == 60


def test_get_cooldown_config_is_cached():
    assert ci.get_cooldown_config() is ci.get_cooldown_config()


def test_get_cooldown_state_is_cached():
    assert ci.get_cooldown_state() is ci.get_cooldown_state()


def test_reset_creates_new_instances():
    s1 = ci.get_cooldown_state()
    c1 = ci.get_cooldown_config()
    ci.reset_cooldown()
    assert ci.get_cooldown_state() is not s1
    assert ci.get_cooldown_config() is not c1


def test_filter_allows_first_event():
    events = [_ev("job_x")]
    result = ci.filter_cooled_down(events)
    assert len(result) == 1


def test_filter_suppresses_duplicate_within_period():
    ev = _ev("job_x")
    ci.filter_cooled_down([ev])  # first pass — recorded
    result = ci.filter_cooled_down([ev])  # second pass — suppressed
    assert result == []


def test_filter_multiple_jobs_independently():
    events = [_ev("job_a"), _ev("job_b")]
    result = ci.filter_cooled_down(events)
    assert len(result) == 2
