"""Integration-level tests for cron_watcher.envelope_integration."""
import pytest

from cron_watcher.envelope_integration import (
    get_envelope_config,
    reset_envelope_config,
    wrapped_failures,
)
from cron_watcher.log_parser import CronEvent


def _ev(job: str = "/usr/bin/job") -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T04:00:00",
        job=job,
        exit_status=2,
        raw_line="CRON[1]: CMD",
        is_failure=True,
    )


@pytest.fixture(autouse=True)
def _reset():
    reset_envelope_config()
    yield
    reset_envelope_config()


def test_get_envelope_config_returns_instance():
    cfg = get_envelope_config()
    assert cfg is not None


def test_get_envelope_config_is_cached():
    cfg1 = get_envelope_config()
    cfg2 = get_envelope_config()
    assert cfg1 is cfg2


def test_reset_creates_new_instance():
    cfg1 = get_envelope_config()
    reset_envelope_config()
    cfg2 = get_envelope_config()
    assert cfg1 is not cfg2


def test_get_envelope_config_reads_raw():
    cfg = get_envelope_config({"envelope": {"source_tag": "test-host"}})
    assert cfg.source_tag == "test-host"


def test_wrapped_failures_returns_dict():
    events = [_ev(), _ev("/usr/bin/other")]
    result = wrapped_failures(events)
    assert isinstance(result, dict)
    assert result["event_count"] == 2


def test_wrapped_failures_uses_cached_config():
    get_envelope_config({"envelope": {"source_tag": "cached-tag"}})
    result = wrapped_failures([_ev()])
    assert result["source"] == "cached-tag"
