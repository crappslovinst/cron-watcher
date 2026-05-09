"""Unit tests for cron_watcher.envelope."""
import socket
from datetime import datetime, timezone

import pytest

from cron_watcher.envelope import (
    EnvelopeConfig,
    envelope_config_from_dict,
    wrap,
)
from cron_watcher.log_parser import CronEvent


def _ev(job: str = "/usr/bin/backup", exit_status: int = 1) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T03:00:01",
        job=job,
        exit_status=exit_status,
        raw_line=f"CRON[999]: ({job}) CMD (exit {exit_status})",
        is_failure=exit_status != 0,
    )


def test_envelope_config_defaults():
    cfg = envelope_config_from_dict({})
    assert cfg.include_hostname is True
    assert cfg.include_timestamp is True
    assert cfg.source_tag == "cron-watcher"
    assert cfg.extra_fields == {}


def test_envelope_config_from_dict():
    raw = {
        "envelope": {
            "include_hostname": False,
            "source_tag": "my-server",
            "extra_fields": {"env": "prod"},
        }
    }
    cfg = envelope_config_from_dict(raw)
    assert cfg.include_hostname is False
    assert cfg.source_tag == "my-server"
    assert cfg.extra_fields == {"env": "prod"}


def test_wrap_includes_event_count():
    cfg = EnvelopeConfig(include_hostname=False, include_timestamp=False)
    events = [_ev(), _ev("/usr/bin/cleanup")]
    result = wrap(events, cfg)
    assert result["event_count"] == 2
    assert len(result["events"]) == 2


def test_wrap_includes_hostname():
    cfg = EnvelopeConfig(include_hostname=True, include_timestamp=False)
    result = wrap([_ev()], cfg)
    assert result["hostname"] == socket.gethostname()


def test_wrap_omits_hostname_when_disabled():
    cfg = EnvelopeConfig(include_hostname=False, include_timestamp=False)
    result = wrap([_ev()], cfg)
    assert "hostname" not in result


def test_wrap_includes_timestamp():
    cfg = EnvelopeConfig(include_hostname=False, include_timestamp=True)
    result = wrap([_ev()], cfg)
    assert "timestamp" in result
    # basic ISO-ish format check
    assert "T" in result["timestamp"]


def test_wrap_extra_fields():
    cfg = EnvelopeConfig(
        include_hostname=False,
        include_timestamp=False,
        extra_fields={"region": "us-east-1"},
    )
    result = wrap([_ev()], cfg)
    assert result["extra"] == {"region": "us-east-1"}


def test_wrap_no_extra_fields_key_absent():
    cfg = EnvelopeConfig(include_hostname=False, include_timestamp=False)
    result = wrap([_ev()], cfg)
    assert "extra" not in result


def test_wrap_source_tag():
    cfg = EnvelopeConfig(
        include_hostname=False, include_timestamp=False, source_tag="ci-runner"
    )
    result = wrap([_ev()], cfg)
    assert result["source"] == "ci-runner"
