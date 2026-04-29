"""Tests for cron_watcher.metrics_endpoint."""

import json
import socket
import time
import urllib.request

import pytest
from cron_watcher.metrics_endpoint import MetricsServer


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def metrics_server():
    port = _free_port()
    data = {"events_processed": 7, "failures_detected": 2}
    srv = MetricsServer("127.0.0.1", port, lambda: data)
    srv.start()
    time.sleep(0.05)  # let the server thread spin up
    yield srv, port, data
    srv.stop()


def test_metrics_returns_200(metrics_server):
    _, port, _ = metrics_server
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
    assert resp.status == 200


def test_metrics_content_type(metrics_server):
    _, port, _ = metrics_server
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
    assert "application/json" in resp.headers.get("Content-Type", "")


def test_metrics_returns_snapshot(metrics_server):
    _, port, data = metrics_server
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
    body = json.loads(resp.read())
    assert body["events_processed"] == data["events_processed"]
    assert body["failures_detected"] == data["failures_detected"]


def test_unknown_path_returns_404(metrics_server):
    _, port, _ = metrics_server
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown")
        pytest.fail("Expected HTTPError")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_stop_shuts_down_server(metrics_server):
    srv, port, _ = metrics_server
    srv.stop()
    with pytest.raises(Exception):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=1)
