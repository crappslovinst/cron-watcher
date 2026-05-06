"""Tests for cron_watcher.silence and cron_watcher.silence_integration."""

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.silence import (
    SilenceWindow,
    filter_silenced,
    is_silenced,
    silence_config_from_dict,
)
from cron_watcher.silence_integration import (
    apply_silence,
    get_silence_windows,
    reset_silence_windows,
)


def _ev(command: str) -> CronEvent:
    return CronEvent(timestamp="2024-01-15T02:00:00", command=command, exit_status=1, is_failure=True)


@pytest.fixture(autouse=True)
def _reset():
    reset_silence_windows()
    yield
    reset_silence_windows()


# ---------------------------------------------------------------------------
# SilenceWindow unit tests
# ---------------------------------------------------------------------------

def test_window_matches_job_by_regex():
    w = SilenceWindow(pattern=r"backup.*", start=time(1, 0), end=time(3, 0))
    assert w.matches_job("backup_daily.sh")
    assert not w.matches_job("send_report.sh")


def test_window_active_within_range():
    w = SilenceWindow(pattern=".*", start=time(1, 0), end=time(3, 0))
    assert w.is_active(datetime(2024, 1, 15, 2, 0))
    assert not w.is_active(datetime(2024, 1, 15, 4, 0))


def test_window_overnight_range():
    w = SilenceWindow(pattern=".*", start=time(23, 0), end=time(1, 0))
    assert w.is_active(datetime(2024, 1, 15, 23, 30))
    assert w.is_active(datetime(2024, 1, 15, 0, 30))
    assert not w.is_active(datetime(2024, 1, 15, 12, 0))


def test_window_day_filter_respected():
    # days=[0] means Monday only
    w = SilenceWindow(pattern=".*", start=time(0, 0), end=time(23, 59), days=[0])
    monday = datetime(2024, 1, 15, 12, 0)   # Monday
    tuesday = datetime(2024, 1, 16, 12, 0)  # Tuesday
    assert w.is_active(monday)
    assert not w.is_active(tuesday)


# ---------------------------------------------------------------------------
# silence_config_from_dict
# ---------------------------------------------------------------------------

def test_silence_config_from_dict_parses_entry():
    raw = [{"pattern": r"backup", "start": "02:00", "end": "04:00", "days": [0, 6]}]
    windows = silence_config_from_dict(raw)
    assert len(windows) == 1
    assert windows[0].start == time(2, 0)
    assert windows[0].days == [0, 6]


def test_silence_config_empty_list():
    assert silence_config_from_dict([]) == []


# ---------------------------------------------------------------------------
# is_silenced / filter_silenced
# ---------------------------------------------------------------------------

def test_is_silenced_returns_true_when_active():
    w = SilenceWindow(pattern="backup", start=time(1, 0), end=time(3, 0))
    ev = _ev("backup_weekly.sh")
    assert is_silenced(ev, [w], now=datetime(2024, 1, 15, 2, 0))


def test_is_silenced_returns_false_outside_window():
    w = SilenceWindow(pattern="backup", start=time(1, 0), end=time(3, 0))
    ev = _ev("backup_weekly.sh")
    assert not is_silenced(ev, [w], now=datetime(2024, 1, 15, 5, 0))


def test_filter_silenced_removes_matching_events():
    w = SilenceWindow(pattern="backup", start=time(1, 0), end=time(3, 0))
    events = [_ev("backup.sh"), _ev("report.sh")]
    result = filter_silenced(events, [w], now=datetime(2024, 1, 15, 2, 0))
    assert len(result) == 1
    assert result[0].command == "report.sh"


# ---------------------------------------------------------------------------
# silence_integration
# ---------------------------------------------------------------------------

def test_get_silence_windows_cached():
    raw = [{"pattern": "x", "start": "00:00", "end": "01:00"}]
    first = get_silence_windows(raw)
    second = get_silence_windows()  # no raw — should reuse cache
    assert first is second


def test_apply_silence_uses_global_windows():
    raw = [{"pattern": "backup", "start": "01:00", "end": "03:00"}]
    get_silence_windows(raw)
    events = [_ev("backup.sh"), _ev("cleanup.sh")]
    result = apply_silence(events, now=datetime(2024, 1, 15, 2, 0))
    assert [e.command for e in result] == ["cleanup.sh"]
