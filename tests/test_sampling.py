"""Unit tests for cron_watcher.sampling."""
from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.sampling import (
    SamplingConfig,
    sample_events,
    sampling_config_from_dict,
)


def _ev(job: str = "/usr/bin/backup", failure: bool = True) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T03:00:00",
        job=job,
        exit_status=1 if failure else 0,
        is_failure=failure,
        raw="raw line",
    )


# ---------------------------------------------------------------------------
# config parsing
# ---------------------------------------------------------------------------

def test_sampling_config_defaults():
    cfg = sampling_config_from_dict({})
    assert cfg.enabled is False
    assert cfg.rate == 1.0
    assert cfg.always_include == []


def test_sampling_config_from_dict():
    raw = {"sampling": {"enabled": True, "rate": 0.5, "always_include": ["backup"]}}
    cfg = sampling_config_from_dict(raw)
    assert cfg.enabled is True
    assert cfg.rate == 0.5
    assert cfg.always_include == ["backup"]


# ---------------------------------------------------------------------------
# sample_events behaviour
# ---------------------------------------------------------------------------

def test_disabled_config_returns_all():
    events = [_ev(), _ev(), _ev()]
    cfg = SamplingConfig(enabled=False, rate=0.1)
    assert sample_events(events, cfg) == events


def test_rate_1_returns_all():
    events = [_ev() for _ in range(10)]
    cfg = SamplingConfig(enabled=True, rate=1.0)
    assert sample_events(events, cfg) == events


def test_rate_0_drops_all_non_pinned():
    events = [_ev("/usr/bin/job") for _ in range(20)]
    cfg = SamplingConfig(enabled=True, rate=0.0)
    # With rate=0.0 random() is always >= 0.0, so nothing passes unless pinned
    result = sample_events(events, cfg, rng=random.Random(42))
    assert result == []


def test_always_include_preserves_pinned_jobs():
    pinned = _ev("/usr/bin/critical")
    other = _ev("/usr/bin/routine")
    events = [pinned, other]
    cfg = SamplingConfig(enabled=True, rate=0.0, always_include=["critical"])
    result = sample_events(events, cfg, rng=random.Random(0))
    assert pinned in result
    assert other not in result


def test_sampling_reduces_event_count():
    rng = random.Random(99)
    events = [_ev() for _ in range(1000)]
    cfg = SamplingConfig(enabled=True, rate=0.2)
    result = sample_events(events, cfg, rng=rng)
    # Expect roughly 200; allow wide tolerance
    assert 100 < len(result) < 400


def test_always_include_regex_pattern():
    ev1 = _ev("/etc/cron.daily/apt-compat")
    ev2 = _ev("/usr/bin/backup-db")
    cfg = SamplingConfig(enabled=True, rate=0.0, always_include=[r"cron\.daily"])
    result = sample_events([ev1, ev2], cfg, rng=random.Random(0))
    assert ev1 in result
    assert ev2 not in result
