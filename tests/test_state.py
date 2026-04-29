"""Tests for cron_watcher.state."""

import json
import os

import pytest

from cron_watcher.state import WatcherState, load_state, save_state


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def state_path(tmp_path):
    return str(tmp_path / "state.json")


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------


def test_load_state_missing_file_returns_defaults(state_path):
    s = load_state(state_path)
    assert isinstance(s, WatcherState)
    assert s.inode == 0
    assert s.offset == 0
    assert s.total_events_seen == 0


def test_load_state_reads_saved_values(state_path):
    data = {
        "log_path": "/var/log/syslog",
        "inode": 12345,
        "offset": 4096,
        "last_event_ts": "2024-01-15T10:00:00",
        "total_events_seen": 42,
        "total_failures_seen": 3,
        "extra": {},
    }
    with open(state_path, "w") as fh:
        json.dump(data, fh)

    s = load_state(state_path)
    assert s.inode == 12345
    assert s.offset == 4096
    assert s.total_events_seen == 42
    assert s.total_failures_seen == 3
    assert s.last_event_ts == "2024-01-15T10:00:00"


def test_load_state_corrupt_file_returns_defaults(state_path):
    with open(state_path, "w") as fh:
        fh.write("not json{{")
    s = load_state(state_path)
    assert s.inode == 0


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------


def test_save_state_creates_file(state_path):
    s = WatcherState(log_path="/var/log/syslog", inode=99, offset=512)
    save_state(state_path, s)
    assert os.path.exists(state_path)


def test_save_state_roundtrip(state_path):
    original = WatcherState(
        log_path="/var/log/cron",
        inode=7,
        offset=1024,
        total_events_seen=10,
        total_failures_seen=2,
    )
    save_state(state_path, original)
    loaded = load_state(state_path)
    assert loaded.inode == 7
    assert loaded.offset == 1024
    assert loaded.total_events_seen == 10
    assert loaded.total_failures_seen == 2


def test_save_state_creates_parent_dirs(tmp_path):
    deep_path = str(tmp_path / "a" / "b" / "c" / "state.json")
    save_state(deep_path, WatcherState(inode=1))
    assert os.path.exists(deep_path)


def test_save_state_no_tmp_file_left(state_path):
    save_state(state_path, WatcherState())
    assert not os.path.exists(state_path + ".tmp")
