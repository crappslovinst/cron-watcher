"""Tests for cron_watcher.snapshot and snapshot_integration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cron_watcher.snapshot import SnapshotConfig, snapshot_config_from_dict, write_snapshot
from cron_watcher.snapshot_integration import (
    do_snapshot,
    get_snapshot_config,
    reset_snapshot_config,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _metrics() -> dict:
    return {"events_total": 5, "failures_total": 2}


def _state() -> dict:
    return {"offset": 1024, "inode": 999}


# ---------------------------------------------------------------------------
# SnapshotConfig
# ---------------------------------------------------------------------------

def test_snapshot_config_defaults():
    cfg = snapshot_config_from_dict({})
    assert cfg.enabled is False
    assert cfg.pretty is False
    assert "snapshot.json" in cfg.path


def test_snapshot_config_from_dict():
    cfg = snapshot_config_from_dict({"enabled": True, "path": "/tmp/snap.json", "pretty": True})
    assert cfg.enabled is True
    assert cfg.path == "/tmp/snap.json"
    assert cfg.pretty is True


# ---------------------------------------------------------------------------
# write_snapshot
# ---------------------------------------------------------------------------

def test_write_snapshot_disabled_returns_false(tmp_path):
    cfg = SnapshotConfig(enabled=False, path=str(tmp_path / "snap.json"))
    assert write_snapshot(cfg, _metrics, _state) is False
    assert not (tmp_path / "snap.json").exists()


def test_write_snapshot_creates_file(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path / "snap.json"))
    result = write_snapshot(cfg, _metrics, _state)
    assert result is True
    assert (tmp_path / "snap.json").exists()


def test_write_snapshot_valid_json(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path / "snap.json"))
    write_snapshot(cfg, _metrics, _state, extra={"daemon_pid": 42})
    data = json.loads((tmp_path / "snap.json").read_text())
    assert data["metrics"]["events_total"] == 5
    assert data["state"]["offset"] == 1024
    assert data["extra"]["daemon_pid"] == 42
    assert "timestamp" in data


def test_write_snapshot_pretty(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path / "snap.json"), pretty=True)
    write_snapshot(cfg, _metrics, _state)
    raw = (tmp_path / "snap.json").read_text()
    assert "\n" in raw  # indented


def test_write_snapshot_bad_path_returns_false():
    cfg = SnapshotConfig(enabled=True, path="/no_such_root_dir/deep/snap.json")
    # Should not raise; should return False if mkdir fails
    with patch("cron_watcher.snapshot.Path.mkdir", side_effect=OSError("no perms")):
        result = write_snapshot(cfg, _metrics, _state)
    assert result is False


# ---------------------------------------------------------------------------
# snapshot_integration
# ---------------------------------------------------------------------------

def test_get_snapshot_config_is_cached():
    reset_snapshot_config()
    a = get_snapshot_config({"enabled": False})
    b = get_snapshot_config({"enabled": True})  # second call should return cached
    assert a is b
    reset_snapshot_config()


def test_do_snapshot_disabled_returns_false():
    reset_snapshot_config()
    with patch("cron_watcher.snapshot_integration.get_snapshot_config",
               return_value=SnapshotConfig(enabled=False)):
        assert do_snapshot() is False
    reset_snapshot_config()
