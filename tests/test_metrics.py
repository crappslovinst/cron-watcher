"""Tests for cron_watcher.metrics."""

import time
import pytest
from cron_watcher.metrics import Metrics, MetricsCollector


@pytest.fixture
def mc():
    c = MetricsCollector()
    return c


def test_initial_snapshot_zeros(mc):
    s = mc.snapshot()
    assert s["events_processed"] == 0
    assert s["failures_detected"] == 0
    assert s["alerts_sent"] == 0
    assert s["alert_errors"] == 0
    assert s["log_rotations"] == 0
    assert s["last_alert_at"] is None


def test_uptime_increases(mc):
    s1 = mc.snapshot()
    time.sleep(0.05)
    s2 = mc.snapshot()
    assert s2["uptime_seconds"] >= s1["uptime_seconds"]


def test_inc_events(mc):
    mc.inc_events(3)
    assert mc.snapshot()["events_processed"] == 3


def test_inc_failures(mc):
    mc.inc_failures(2)
    assert mc.snapshot()["failures_detected"] == 2


def test_inc_alerts_sent_sets_last_alert_at(mc):
    before = time.time()
    mc.inc_alerts_sent(1)
    s = mc.snapshot()
    assert s["alerts_sent"] == 1
    assert s["last_alert_at"] is not None
    assert s["last_alert_at"] >= before


def test_inc_alert_errors(mc):
    mc.inc_alert_errors()
    assert mc.snapshot()["alert_errors"] == 1


def test_inc_log_rotations(mc):
    mc.inc_log_rotations()
    assert mc.snapshot()["log_rotations"] == 1


def test_reset_clears_counters(mc):
    mc.inc_events(10)
    mc.inc_failures(5)
    mc.reset()
    s = mc.snapshot()
    assert s["events_processed"] == 0
    assert s["failures_detected"] == 0


def test_metrics_to_dict_keys():
    m = Metrics()
    d = m.to_dict()
    expected_keys = {
        "uptime_seconds", "events_processed", "failures_detected",
        "alerts_sent", "alert_errors", "last_alert_at", "log_rotations",
    }
    assert set(d.keys()) == expected_keys


def test_thread_safety(mc):
    import threading

    def worker():
        for _ in range(100):
            mc.inc_events()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert mc.snapshot()["events_processed"] == 500
