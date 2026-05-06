"""Tests for cron_watcher.escalation."""
import time
from datetime import datetime, timezone, timedelta

import pytest

from cron_watcher.escalation import (
    EscalationConfig,
    EscalationTracker,
    escalation_config_from_dict,
)


@pytest.fixture
def tracker():
    cfg = EscalationConfig(enabled=True, threshold=3, cooldown=60)
    return EscalationTracker(config=cfg)


def test_disabled_config_never_escalates():
    cfg = EscalationConfig(enabled=False, threshold=1)
    t = EscalationTracker(config=cfg)
    for _ in range(10):
        assert t.record_failure("backup") is False


def test_below_threshold_does_not_escalate(tracker):
    assert tracker.record_failure("backup") is False  # 1
    assert tracker.record_failure("backup") is False  # 2


def test_at_threshold_escalates(tracker):
    tracker.record_failure("backup")  # 1
    tracker.record_failure("backup")  # 2
    assert tracker.record_failure("backup") is True  # 3 — threshold hit


def test_within_cooldown_suppresses_second_escalation(tracker):
    for _ in range(3):
        tracker.record_failure("backup")
    # first escalation fired; next failure should be suppressed
    assert tracker.record_failure("backup") is False


def test_after_cooldown_escalates_again():
    cfg = EscalationConfig(enabled=True, threshold=2, cooldown=0)
    t = EscalationTracker(config=cfg)
    t.record_failure("sync")  # 1
    assert t.record_failure("sync") is True  # 2 — escalate
    # cooldown=0 so next batch should also escalate
    assert t.record_failure("sync") is True


def test_record_success_resets_counter(tracker):
    tracker.record_failure("backup")  # 1
    tracker.record_failure("backup")  # 2
    tracker.record_success("backup")
    assert tracker.consecutive_failures("backup") == 0
    # need to reach threshold again from scratch
    assert tracker.record_failure("backup") is False  # 1 again


def test_independent_jobs_tracked_separately(tracker):
    tracker.record_failure("job_a")  # 1
    tracker.record_failure("job_a")  # 2
    tracker.record_failure("job_b")  # 1 for b
    assert tracker.consecutive_failures("job_a") == 2
    assert tracker.consecutive_failures("job_b") == 1


def test_escalation_config_from_dict():
    cfg = escalation_config_from_dict({"enabled": True, "threshold": 5, "cooldown": 300})
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.cooldown == 300


def test_escalation_config_from_dict_defaults():
    cfg = escalation_config_from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.cooldown == 1800
