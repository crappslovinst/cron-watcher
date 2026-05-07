"""Tests for cron_watcher.heartbeat."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cron_watcher.heartbeat import (
    HeartbeatConfig,
    HeartbeatState,
    heartbeat_config_from_dict,
    ping,
    should_ping,
)


@pytest.fixture()
def cfg() -> HeartbeatConfig:
    return HeartbeatConfig(enabled=True, url="http://example.com/ping", interval_seconds=60)


@pytest.fixture()
def state() -> HeartbeatState:
    return HeartbeatState()


# --- config parsing ---

def test_heartbeat_config_defaults():
    hb = heartbeat_config_from_dict({})
    assert hb.enabled is False
    assert hb.url == ""
    assert hb.interval_seconds == 60
    assert hb.timeout_seconds == 10


def test_heartbeat_config_from_dict():
    raw = {"heartbeat": {"enabled": True, "url": "http://hc.example/abc", "interval_seconds": 30}}
    hb = heartbeat_config_from_dict(raw)
    assert hb.enabled is True
    assert hb.url == "http://hc.example/abc"
    assert hb.interval_seconds == 30


# --- should_ping ---

def test_should_ping_true_when_no_previous(cfg, state):
    assert should_ping(cfg, state) is True


def test_should_ping_false_when_recent(cfg, state):
    state.last_ping_ts = time.time()
    assert should_ping(cfg, state) is False


def test_should_ping_true_after_interval(cfg, state):
    state.last_ping_ts = time.time() - 120
    assert should_ping(cfg, state) is True


def test_should_ping_false_when_disabled(state):
    disabled = HeartbeatConfig(enabled=False, url="http://example.com/ping")
    assert should_ping(disabled, state) is False


# --- ping ---

def test_ping_disabled_returns_false(state):
    disabled = HeartbeatConfig(enabled=False)
    result = ping(disabled, state)
    assert result is False
    assert state.total_pings == 0


def test_ping_success_updates_state(cfg, state):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = ping(cfg, state)

    assert result is True
    assert state.last_ping_ok is True
    assert state.total_pings == 1
    assert state.total_failures == 0
    assert state.last_ping_ts is not None


def test_ping_failure_increments_failure_count(cfg, state):
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = ping(cfg, state)

    assert result is False
    assert state.last_ping_ok is False
    assert state.total_pings == 1
    assert state.total_failures == 1


def test_ping_sends_custom_headers(cfg, state):
    cfg.headers = {"Authorization": "Bearer token123"}
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        ping(cfg, state)
        request_obj = mock_open.call_args[0][0]
        assert request_obj.get_header("Authorization") == "Bearer token123"
