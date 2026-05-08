"""Tests for cron_watcher.ratelimit and ratelimit_integration."""
from __future__ import annotations

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.ratelimit import RateLimitConfig, RateLimiter, ratelimit_config_from_dict
from cron_watcher import ratelimit_integration as rl_int


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ev(job: str = "backup") -> CronEvent:
    return CronEvent(timestamp="2024-01-01T00:00:00", job=job, message="err",
                     exit_status=1, is_failure=True, raw="")


@pytest.fixture(autouse=True)
def _reset():
    rl_int.reset_rate_limiter()
    yield
    rl_int.reset_rate_limiter()


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

def test_ratelimit_config_defaults():
    cfg = RateLimitConfig()
    assert cfg.enabled is False
    assert cfg.max_alerts == 5
    assert cfg.window_seconds == 3600


def test_ratelimit_config_from_dict():
    cfg = ratelimit_config_from_dict({"ratelimit": {"enabled": True, "max_alerts": 3, "window_seconds": 60}})
    assert cfg.enabled is True
    assert cfg.max_alerts == 3
    assert cfg.window_seconds == 60


def test_ratelimit_config_from_dict_empty():
    cfg = ratelimit_config_from_dict({})
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

def test_disabled_allows_unlimited():
    limiter = RateLimiter(RateLimitConfig(enabled=False, max_alerts=1))
    for _ in range(10):
        assert limiter.is_allowed("job") is True
        limiter.record("job")


def test_allows_up_to_max():
    cfg = RateLimitConfig(enabled=True, max_alerts=3, window_seconds=60)
    limiter = RateLimiter(cfg)
    now = 1000.0
    for _ in range(3):
        assert limiter.is_allowed("job", now=now) is True
        limiter.record("job", now=now)
    assert limiter.is_allowed("job", now=now) is False


def test_window_slides_and_allows_again():
    cfg = RateLimitConfig(enabled=True, max_alerts=2, window_seconds=60)
    limiter = RateLimiter(cfg)
    limiter.record("job", now=1000.0)
    limiter.record("job", now=1001.0)
    # still blocked
    assert limiter.is_allowed("job", now=1059.0) is False
    # after window expires for first record
    assert limiter.is_allowed("job", now=1061.0) is True


def test_remaining_decrements():
    cfg = RateLimitConfig(enabled=True, max_alerts=3, window_seconds=60)
    limiter = RateLimiter(cfg)
    now = 500.0
    assert limiter.remaining("job", now=now) == 3
    limiter.record("job", now=now)
    assert limiter.remaining("job", now=now) == 2


def test_independent_jobs():
    cfg = RateLimitConfig(enabled=True, max_alerts=1, window_seconds=60)
    limiter = RateLimiter(cfg)
    now = 100.0
    limiter.record("a", now=now)
    assert limiter.is_allowed("a", now=now) is False
    assert limiter.is_allowed("b", now=now) is True


# ---------------------------------------------------------------------------
# ratelimit_integration
# ---------------------------------------------------------------------------

def test_get_rate_limiter_returns_same_instance():
    a = rl_int.get_rate_limiter()
    b = rl_int.get_rate_limiter()
    assert a is b


def test_reset_creates_new_instance():
    a = rl_int.get_rate_limiter()
    rl_int.reset_rate_limiter()
    b = rl_int.get_rate_limiter()
    assert a is not b


def test_ratelimited_failures_passes_within_limit():
    cfg = RateLimitConfig(enabled=True, max_alerts=2, window_seconds=60)
    rl_int.reset_rate_limiter(cfg)
    events = [_ev("backup"), _ev("backup"), _ev("backup")]
    result = rl_int.ratelimited_failures(events)
    assert len(result) == 2


def test_ratelimited_failures_disabled_passes_all():
    cfg = RateLimitConfig(enabled=False)
    rl_int.reset_rate_limiter(cfg)
    events = [_ev() for _ in range(20)]
    assert len(rl_int.ratelimited_failures(events)) == 20
