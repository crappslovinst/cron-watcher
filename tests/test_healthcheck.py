"""Tests for the healthcheck HTTP server."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from cron_watcher.healthcheck import HealthCheckServer, _make_handler, build_status


FREE_PORT = 19876


@pytest.fixture()
def status_data():
    return {"status": "ok", "pending_failures": 0}


@pytest.fixture()
def server(status_data):
    srv = HealthCheckServer("127.0.0.1", FREE_PORT, lambda: status_data)
    srv.start()
    time.sleep(0.05)  # let the thread spin up
    yield srv
    srv.stop()


def test_health_endpoint_returns_200(server, status_data):
    url = f"http://127.0.0.1:{FREE_PORT}/health"
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 200
        body = json.loads(resp.read())
    assert body["status"] == "ok"


def test_health_endpoint_reflects_status(status_data, server):
    status_data["pending_failures"] = 3
    url = f"http://127.0.0.1:{FREE_PORT}/health"
    with urllib.request.urlopen(url) as resp:
        body = json.loads(resp.read())
    assert body["pending_failures"] == 3


def test_unknown_path_returns_404(server):
    url = f"http://127.0.0.1:{FREE_PORT}/unknown"
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(url)
    assert exc_info.value.code == 404


def test_stop_is_idempotent():
    srv = HealthCheckServer("127.0.0.1", FREE_PORT + 1, lambda: {})
    srv.start()
    time.sleep(0.05)
    srv.stop()
    srv.stop()  # should not raise


def test_build_status_ok():
    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    mock_scheduler.run_count = 5
    mock_scheduler.last_run = None

    mock_daemon = MagicMock()
    mock_daemon.pending_events = ["e1", "e2"]
    mock_daemon.scheduler = mock_scheduler

    status = build_status(mock_daemon)

    assert status["status"] == "ok"
    assert status["pending_failures"] == 2
    assert status["scheduler"]["running"] is True
    assert status["scheduler"]["run_count"] == 5
    assert status["scheduler"]["last_run"] is None


def test_build_status_no_scheduler():
    mock_daemon = MagicMock()
    mock_daemon.pending_events = []
    mock_daemon.scheduler = None

    status = build_status(mock_daemon)
    assert status["scheduler"]["running"] is False
    assert status["scheduler"]["run_count"] == 0
