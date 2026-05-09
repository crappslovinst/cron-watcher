"""Unit tests for cron_watcher.backoff."""
from __future__ import annotations

import pytest

from cron_watcher.backoff import BackoffConfig, BackoffTracker, backoff_config_from_dict


@pytest.fixture()
def tracker() -> BackoffTracker:
    cfg = BackoffConfig(base_delay=10.0, multiplier=2.0, max_delay=100.0, reset_after=200.0)
    return BackoffTracker(config=cfg)


def test_backoff_config_defaults():
    cfg = backoff_config_from_dict({})
    assert cfg.enabled is True
    assert cfg.base_delay == 60.0
    assert cfg.multiplier == 2.0
    assert cfg.max_delay == 3600.0


def test_backoff_config_from_dict():
    cfg = backoff_config_from_dict({"backoff": {"base_delay": 30.0, "multiplier": 3.0}})
    assert cfg.base_delay == 30.0
    assert cfg.multiplier == 3.0


def test_first_alert_always_allowed(tracker):
    assert tracker.is_allowed("job_a", now=0.0) is True


def test_second_alert_suppressed_within_delay(tracker):
    tracker.record_alert("job_a", now=0.0)   # attempt 0 -> delay = 10 s
    assert tracker.is_allowed("job_a", now=5.0) is False


def test_second_alert_allowed_after_delay(tracker):
    tracker.record_alert("job_a", now=0.0)
    assert tracker.is_allowed("job_a", now=10.0) is True


def test_delay_grows_exponentially(tracker):
    tracker.record_alert("job_a", now=0.0)   # delay = 10
    tracker.record_alert("job_a", now=10.0)  # delay = 20
    # next allowed at 10 + 20 = 30
    assert tracker.is_allowed("job_a", now=25.0) is False
    assert tracker.is_allowed("job_a", now=30.0) is True


def test_delay_capped_at_max(tracker):
    # Force many attempts
    t = 0.0
    for _ in range(10):
        tracker.record_alert("job_a", now=t)
        t += 200.0
    st = tracker._get("job_a")
    delay = min(
        tracker.config.base_delay * (tracker.config.multiplier ** (st.attempt - 1)),
        tracker.config.max_delay,
    )
    assert delay == tracker.config.max_delay


def test_reset_job_clears_state(tracker):
    tracker.record_alert("job_a", now=0.0)
    tracker.reset_job("job_a")
    assert tracker.is_allowed("job_a", now=0.0) is True


def test_stale_state_is_reset(tracker):
    tracker.record_alert("job_a", now=0.0)
    # reset_after=200, so at t=201 the state should be discarded
    assert tracker.is_allowed("job_a", now=201.0) is True


def test_disabled_config_always_allows():
    cfg = BackoffConfig(enabled=False)
    t = BackoffTracker(config=cfg)
    t.record_alert("job_a", now=0.0)
    assert t.is_allowed("job_a", now=0.0) is True


def test_independent_jobs_tracked_separately(tracker):
    tracker.record_alert("job_a", now=0.0)
    assert tracker.is_allowed("job_b", now=0.0) is True
