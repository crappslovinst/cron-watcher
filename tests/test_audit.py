"""Tests for cron_watcher.audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cron_watcher.audit import (
    AuditEntry,
    append_entry,
    build_entry,
    read_entries,
)
from cron_watcher.log_parser import CronEvent


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ev(job: str = "backup", exit_status: int = 1) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T03:00:00",
        job=job,
        pid=1234,
        message="exited",
        exit_status=exit_status,
        is_failure=True,
    )


# ---------------------------------------------------------------------------
# build_entry
# ---------------------------------------------------------------------------

def test_build_entry_sets_alert_type():
    entry = build_entry("webhook", [_ev()], success=True)
    assert entry.alert_type == "webhook"


def test_build_entry_counts_events():
    events = [_ev("a"), _ev("b"), _ev("b")]
    entry = build_entry("email", events, success=False, error="timeout")
    assert entry.failure_count == 3


def test_build_entry_deduplicates_job_names():
    events = [_ev("backup"), _ev("backup"), _ev("cleanup")]
    entry = build_entry("webhook", events, success=True)
    assert entry.job_names == ["backup", "cleanup"]


def test_build_entry_captures_error():
    entry = build_entry("webhook", [_ev()], success=False, error="conn refused")
    assert entry.error == "conn refused"
    assert entry.success is False


def test_build_entry_timestamp_is_iso_string():
    entry = build_entry("digest", [_ev()], success=True)
    # should parse without raising
    from datetime import datetime
    datetime.fromisoformat(entry.timestamp)


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

def test_to_dict_round_trips():
    entry = build_entry("webhook", [_ev("myjob")], success=True)
    d = entry.to_dict()
    assert d["alert_type"] == "webhook"
    assert d["job_names"] == ["myjob"]
    assert d["failure_count"] == 1
    assert d["success"] is True
    assert d["error"] is None


# ---------------------------------------------------------------------------
# append_entry / read_entries
# ---------------------------------------------------------------------------

def test_append_creates_file(tmp_path):
    log = tmp_path / "audit" / "audit.log"
    entry = build_entry("webhook", [_ev()], success=True)
    append_entry(log, entry)
    assert log.exists()


def test_append_and_read_round_trip(tmp_path):
    log = tmp_path / "audit.log"
    e1 = build_entry("webhook", [_ev("job1")], success=True)
    e2 = build_entry("email", [_ev("job2")], success=False, error="smtp err")
    append_entry(log, e1)
    append_entry(log, e2)

    entries = read_entries(log)
    assert len(entries) == 2
    assert entries[0].alert_type == "webhook"
    assert entries[1].alert_type == "email"
    assert entries[1].error == "smtp err"


def test_read_entries_missing_file_returns_empty(tmp_path):
    entries = read_entries(tmp_path / "nonexistent.log")
    assert entries == []


def test_read_entries_skips_corrupt_lines(tmp_path):
    log = tmp_path / "audit.log"
    log.write_text("not json\n" + json.dumps(build_entry("webhook", [_ev()], success=True).to_dict()) + "\n")
    entries = read_entries(log)
    assert len(entries) == 1
