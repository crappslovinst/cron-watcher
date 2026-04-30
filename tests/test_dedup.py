"""Unit tests for cron_watcher.dedup."""

import time

import pytest

from cron_watcher.dedup import DedupState, _fingerprint, deduplicate, evict_expired
from cron_watcher.log_parser import CronEvent


def _ev(job: str = "backup", exit_status: int = 1) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-01T00:00:00",
        job_name=job,
        exit_status=exit_status,
        raw_line=f"{job} exited {exit_status}",
        is_failure=True,
    )


def test_fingerprint_is_stable():
    ev = _ev()
    assert _fingerprint(ev) == _fingerprint(ev)


def test_fingerprint_differs_by_job():
    assert _fingerprint(_ev("a")) != _fingerprint(_ev("b"))


def test_fingerprint_differs_by_exit_status():
    assert _fingerprint(_ev(exit_status=1)) != _fingerprint(_ev(exit_status=2))


def test_first_occurrence_passes_through():
    state = DedupState()
    events = [_ev("job1"), _ev("job2")]
    result = deduplicate(events, state, window_seconds=300, now=1000.0)
    assert result == events


def test_duplicate_within_window_suppressed():
    state = DedupState()
    ev = _ev()
    deduplicate([ev], state, window_seconds=300, now=1000.0)
    result = deduplicate([ev], state, window_seconds=300, now=1100.0)
    assert result == []


def test_duplicate_after_window_passes_through():
    state = DedupState()
    ev = _ev()
    deduplicate([ev], state, window_seconds=300, now=1000.0)
    result = deduplicate([ev], state, window_seconds=300, now=1301.0)
    assert len(result) == 1


def test_different_jobs_both_pass_through():
    state = DedupState()
    events = [_ev("job_a"), _ev("job_b")]
    deduplicate(events, state, window_seconds=300, now=1000.0)
    result = deduplicate([_ev("job_c")], state, window_seconds=300, now=1050.0)
    assert len(result) == 1


def test_evict_removes_stale_entries():
    state = DedupState()
    ev = _ev()
    deduplicate([ev], state, window_seconds=300, now=1000.0)
    evict_expired(state, window_seconds=300, now=1400.0)
    assert state.seen == {}


def test_evict_keeps_fresh_entries():
    state = DedupState()
    ev = _ev()
    deduplicate([ev], state, window_seconds=300, now=1000.0)
    evict_expired(state, window_seconds=300, now=1100.0)
    assert len(state.seen) == 1
