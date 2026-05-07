"""Tests for cron_watcher/cooldown.py"""
import time
import pytest
from cron_watcher.cooldown import CooldownConfig, CooldownState, cooldown_config_from_dict


@pytest.fixture()
def state() -> CooldownState:
    return CooldownState()


@pytest.fixture()
def cfg() -> CooldownConfig:
    return CooldownConfig(enabled=True, period=60)


def test_cooldown_config_defaults():
    c = cooldown_config_from_dict({})
    assert c.enabled is True
    assert c.period == 300


def test_cooldown_config_from_dict():
    c = cooldown_config_from_dict({"cooldown": {"enabled": False, "period": 120}})
    assert c.enabled is False
    assert c.period == 120


def test_first_alert_is_allowed(state, cfg):
    assert state.check_and_record("backup", cfg) is True


def test_second_alert_within_period_is_suppressed(state, cfg):
    t0 = time.monotonic()
    state.check_and_record("backup", cfg, now=t0)
    # 10 seconds later — still within 60 s period
    assert state.check_and_record("backup", cfg, now=t0 + 10) is False


def test_alert_allowed_after_period_expires(state, cfg):
    t0 = time.monotonic()
    state.check_and_record("backup", cfg, now=t0)
    assert state.check_and_record("backup", cfg, now=t0 + 61) is True


def test_different_jobs_are_independent(state, cfg):
    t0 = time.monotonic()
    state.check_and_record("job_a", cfg, now=t0)
    # job_b has never been seen — should pass
    assert state.check_and_record("job_b", cfg, now=t0 + 5) is True


def test_disabled_config_always_allows(state):
    cfg = CooldownConfig(enabled=False, period=3600)
    t0 = time.monotonic()
    state.check_and_record("backup", cfg, now=t0)
    assert state.check_and_record("backup", cfg, now=t0 + 1) is True


def test_reset_job_clears_state(state, cfg):
    t0 = time.monotonic()
    state.check_and_record("backup", cfg, now=t0)
    state.reset_job("backup")
    assert state.check_and_record("backup", cfg, now=t0 + 1) is True


def test_reset_all_clears_all_jobs(state, cfg):
    t0 = time.monotonic()
    for job in ("a", "b", "c"):
        state.check_and_record(job, cfg, now=t0)
    state.reset_all()
    for job in ("a", "b", "c"):
        assert state.check_and_record(job, cfg, now=t0 + 1) is True
