"""Tests for cron_watcher.filter."""
import pytest
from cron_watcher.log_parser import CronEvent
from cron_watcher.filter import FilterConfig, apply_filters, filter_config_from_dict


def _ev(command="backup", exit_status=1, extra=None):
    return CronEvent(
        timestamp=None,
        command=command,
        exit_status=exit_status,
        is_failure=exit_status != 0,
        raw="raw",
        extra=extra or {},
    )


def test_no_filters_returns_all():
    events = [_ev("backup"), _ev("cleanup")]
    assert apply_filters(events, FilterConfig()) == events


def test_exclude_jobs_by_exact_pattern():
    events = [_ev("backup"), _ev("cleanup")]
    cfg = FilterConfig(exclude_jobs=["backup"])
    result = apply_filters(events, cfg)
    assert len(result) == 1
    assert result[0].command == "cleanup"


def test_exclude_jobs_by_regex():
    events = [_ev("/usr/bin/backup"), _ev("/usr/bin/cleanup")]
    cfg = FilterConfig(exclude_jobs=[r"backup$"])
    result = apply_filters(events, cfg)
    assert all("backup" not in e.command for e in result)


def test_only_jobs_whitelist():
    events = [_ev("backup"), _ev("cleanup"), _ev("sync")]
    cfg = FilterConfig(only_jobs=["backup", "sync"])
    result = apply_filters(events, cfg)
    assert {e.command for e in result} == {"backup", "sync"}


def test_exclude_exit_codes():
    events = [_ev(exit_status=0), _ev(exit_status=1), _ev(exit_status=2)]
    cfg = FilterConfig(exclude_exit_codes=[0, 2])
    result = apply_filters(events, cfg)
    assert len(result) == 1
    assert result[0].exit_status == 1


def test_min_duration_filter():
    events = [
        _ev(extra={"duration": "5"}),
        _ev(extra={"duration": "15"}),
        _ev(extra={}),
    ]
    cfg = FilterConfig(min_duration_seconds=10)
    result = apply_filters(events, cfg)
    assert len(result) == 1
    assert result[0].extra["duration"] == "15"


def test_filter_config_from_dict():
    raw = {
        "exclude_jobs": ["noisy"],
        "exclude_exit_codes": ["0"],
        "only_jobs": [],
        "min_duration_seconds": 3.5,
    }
    cfg = filter_config_from_dict(raw)
    assert cfg.exclude_jobs == ["noisy"]
    assert cfg.exclude_exit_codes == [0]
    assert cfg.min_duration_seconds == 3.5


def test_combined_filters():
    events = [_ev("backup", 1), _ev("cleanup", 0), _ev("sync", 1)]
    cfg = FilterConfig(exclude_jobs=["cleanup"], exclude_exit_codes=[0])
    result = apply_filters(events, cfg)
    assert {e.command for e in result} == {"backup", "sync"}
