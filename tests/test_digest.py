"""Unit tests for cron_watcher.digest."""
import time
import pytest

from cron_watcher.digest import DigestConfig, DigestState, digest_config_from_dict
from cron_watcher.log_parser import CronEvent


def _ev(job: str = "/usr/bin/backup") -> CronEvent:
    return CronEvent(
        timestamp="2024-01-01T00:00:00",
        job=job,
        exit_status=1,
        raw_line=f"CRON[1]: CMD ({job})",
        is_failure=True,
    )


def test_digest_config_defaults():
    cfg = DigestConfig()
    assert cfg.enabled is False
    assert cfg.interval_seconds == 3600
    assert cfg.min_failures == 1


def test_digest_config_from_dict():
    cfg = digest_config_from_dict({"enabled": True, "interval_seconds": 60, "min_failures": 3})
    assert cfg.enabled is True
    assert cfg.interval_seconds == 60
    assert cfg.min_failures == 3


def test_add_event_grows_pending():
    state = DigestState()
    state.add(_ev())
    assert len(state.pending) == 1


def test_should_flush_disabled_config():
    cfg = DigestConfig(enabled=False)
    state = DigestState(last_flush=time.time() - 9999)
    state.add(_ev())
    assert state.should_flush(cfg) is False


def test_should_flush_not_yet_time():
    cfg = DigestConfig(enabled=True, interval_seconds=3600)
    state = DigestState(last_flush=time.time())
    state.add(_ev())
    assert state.should_flush(cfg) is False


def test_should_flush_time_elapsed():
    cfg = DigestConfig(enabled=True, interval_seconds=60, min_failures=1)
    state = DigestState(last_flush=time.time() - 120)
    state.add(_ev())
    assert state.should_flush(cfg) is True


def test_should_flush_below_min_failures():
    cfg = DigestConfig(enabled=True, interval_seconds=60, min_failures=5)
    state = DigestState(last_flush=time.time() - 120)
    state.add(_ev())
    assert state.should_flush(cfg) is False


def test_flush_returns_events_and_clears():
    state = DigestState()
    state.add(_ev("job1"))
    state.add(_ev("job2"))
    now = time.time() + 1
    events = state.flush(now=now)
    assert len(events) == 2
    assert len(state.pending) == 0
    assert state.last_flush == now


def test_flush_updates_last_flush():
    state = DigestState(last_flush=0.0)
    state.flush(now=1000.0)
    assert state.last_flush == 1000.0
