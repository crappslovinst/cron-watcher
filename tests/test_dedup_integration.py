"""Tests for the process-level dedup singleton."""

import pytest

from cron_watcher.dedup_integration import (
    dedup_failures,
    get_dedup_state,
    reset_dedup_state,
)
from cron_watcher.log_parser import CronEvent


def _ev(job: str = "nightly") -> CronEvent:
    return CronEvent(
        timestamp="2024-06-01T03:00:00",
        job_name=job,
        exit_status=1,
        raw_line=f"{job} failed",
        is_failure=True,
    )


@pytest.fixture(autouse=True)
def _reset():
    reset_dedup_state()
    yield
    reset_dedup_state()


def test_get_dedup_state_returns_instance():
    state = get_dedup_state()
    assert state is not None


def test_get_dedup_state_is_cached():
    s1 = get_dedup_state()
    s2 = get_dedup_state()
    assert s1 is s2


def test_reset_creates_new_instance():
    s1 = get_dedup_state()
    reset_dedup_state()
    s2 = get_dedup_state()
    assert s1 is not s2


def test_dedup_failures_first_call_passes_all():
    events = [_ev("job_a"), _ev("job_b")]
    result = dedup_failures(events, window_seconds=300)
    assert len(result) == 2


def test_dedup_failures_second_call_suppresses_duplicates():
    ev = _ev()
    dedup_failures([ev], window_seconds=300)
    result = dedup_failures([ev], window_seconds=300)
    assert result == []


def test_dedup_failures_empty_list():
    assert dedup_failures([], window_seconds=300) == []
