"""Integration tests for cron_watcher.digest_integration."""
import time
import pytest

from cron_watcher.log_parser import CronEvent
import cron_watcher.digest_integration as di


def _ev(job: str = "/usr/bin/backup") -> CronEvent:
    return CronEvent(
        timestamp="2024-01-01T00:00:00",
        job=job,
        exit_status=1,
        raw_line=f"CRON[1]: CMD ({job})",
        is_failure=True,
    )


@pytest.fixture(autouse=True)
def _reset():
    di.reset_digest()
    yield
    di.reset_digest()


def test_get_digest_config_returns_instance():
    cfg = di.get_digest_config()
    assert cfg is not None


def test_get_digest_config_is_cached():
    cfg1 = di.get_digest_config()
    cfg2 = di.get_digest_config()
    assert cfg1 is cfg2


def test_get_digest_state_is_cached():
    s1 = di.get_digest_state()
    s2 = di.get_digest_state()
    assert s1 is s2


def test_reset_creates_fresh_state():
    di.accumulate([_ev()])
    di.reset_digest()
    assert len(di.get_digest_state().pending) == 0


def test_accumulate_adds_events():
    di.accumulate([_ev("job1"), _ev("job2")])
    assert len(di.get_digest_state().pending) == 2


def test_try_flush_empty_when_not_due():
    di.reset_digest({"enabled": True, "interval_seconds": 9999, "min_failures": 1})
    di.accumulate([_ev()])
    result = di.try_flush()
    assert result == []


def test_try_flush_returns_events_when_due():
    di.reset_digest({"enabled": True, "interval_seconds": 1, "min_failures": 1})
    di.accumulate([_ev("job_a"), _ev("job_b")])
    # force last_flush into the past
    di.get_digest_state().last_flush = time.time() - 10
    result = di.try_flush()
    assert len(result) == 2
    assert len(di.get_digest_state().pending) == 0


def test_try_flush_disabled_config_returns_empty():
    di.reset_digest({"enabled": False})
    di.get_digest_state().last_flush = time.time() - 99999
    di.accumulate([_ev()])
    assert di.try_flush() == []
