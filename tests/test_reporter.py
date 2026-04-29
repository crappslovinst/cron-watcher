"""Tests for cron_watcher.reporter."""

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.reporter import Report, build_report, format_text_report


@pytest.fixture
def sample_events():
    return [
        CronEvent(
            timestamp="2024-01-15T08:00:01",
            command="/usr/bin/backup.sh",
            raw="Jan 15 08:00:01 host CRON[1]: CMD (/usr/bin/backup.sh)",
            is_failure=True,
            exit_code=1,
            message="Exited with status 1",
        ),
        CronEvent(
            timestamp="2024-01-15T09:00:01",
            command="/usr/bin/backup.sh",
            raw="Jan 15 09:00:01 host CRON[2]: CMD (/usr/bin/backup.sh)",
            is_failure=True,
            exit_code=2,
            message="Exited with status 2",
        ),
        CronEvent(
            timestamp="2024-01-15T10:00:01",
            command="/usr/local/bin/cleanup.sh",
            raw="Jan 15 10:00:01 host CRON[3]: CMD (/usr/local/bin/cleanup.sh)",
            is_failure=True,
            exit_code=127,
            message="command not found",
        ),
    ]


def test_build_report_counts(sample_events):
    report = build_report(sample_events, generated_at="2024-01-15T10:05:00Z")
    assert report.total_failures == 3
    assert report.unique_jobs == 2
    assert report.generated_at == "2024-01-15T10:05:00Z"


def test_build_report_top_failing_jobs(sample_events):
    report = build_report(sample_events)
    assert report.top_failing_jobs[0]["job"] == "/usr/bin/backup.sh"
    assert report.top_failing_jobs[0]["failures"] == 2
    assert report.top_failing_jobs[1]["job"] == "/usr/local/bin/cleanup.sh"
    assert report.top_failing_jobs[1]["failures"] == 1


def test_build_report_top_n_limit(sample_events):
    report = build_report(sample_events, top_n=1)
    assert len(report.top_failing_jobs) == 1


def test_build_report_events_list(sample_events):
    report = build_report(sample_events)
    assert len(report.events) == 3
    first = report.events[0]
    assert first["job"] == "/usr/bin/backup.sh"
    assert first["exit_code"] == 1


def test_build_report_empty():
    report = build_report([])
    assert report.total_failures == 0
    assert report.unique_jobs == 0
    assert report.top_failing_jobs == []


def test_to_dict(sample_events):
    report = build_report(sample_events, generated_at="2024-01-15T10:05:00Z")
    d = report.to_dict()
    assert d["total_failures"] == 3
    assert "events" in d
    assert "top_failing_jobs" in d


def test_format_text_report(sample_events):
    report = build_report(sample_events, generated_at="2024-01-15T10:05:00Z")
    text = format_text_report(report)
    assert "Cron Watcher Report" in text
    assert "/usr/bin/backup.sh" in text
    assert "Total failures" in text
    assert "2x" in text or "2" in text
