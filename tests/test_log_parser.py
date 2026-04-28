"""Tests for the cron log parser module."""

import pytest
from cron_watcher.log_parser import (
    CronEvent,
    filter_failures,
    parse_line,
    parse_log_file,
)


SAMPLE_CMD_LINE = (
    "Jan 15 03:00:01 myhost CRON[12345]: (root) CMD (/usr/bin/backup.sh)"
)
SAMPLE_ERROR_LINE = (
    "Jan 15 03:00:02 myhost CRON[12346]: (root) ERROR (failed to open PAM security)"
)
SAMPLE_EXIT_LINE = (
    "Jan 15 03:00:03 myhost CRON[12347]: (www-data) CMD (exit status 1)"
)
NON_CRON_LINE = "Jan 15 03:00:01 myhost sshd[999]: Accepted password for user"


def test_parse_valid_cmd_line():
    event = parse_line(SAMPLE_CMD_LINE)
    assert event is not None
    assert event.host == "myhost"
    assert event.pid == "12345"
    assert event.job_name == "/usr/bin/backup.sh"
    assert event.is_failure is False


def test_parse_error_line_is_failure():
    event = parse_line(SAMPLE_ERROR_LINE)
    assert event is not None
    assert event.is_failure is True
    assert event.job_name is None


def test_parse_exit_status_is_failure():
    event = parse_line(SAMPLE_EXIT_LINE)
    assert event is not None
    assert event.is_failure is True


def test_parse_non_cron_line_returns_none():
    assert parse_line(NON_CRON_LINE) is None


def test_parse_empty_line_returns_none():
    assert parse_line("") is None


def test_filter_failures():
    events = [
        parse_line(SAMPLE_CMD_LINE),
        parse_line(SAMPLE_ERROR_LINE),
        parse_line(SAMPLE_EXIT_LINE),
    ]
    events = [e for e in events if e is not None]
    failures = filter_failures(events)
    assert len(failures) == 2
    assert all(e.is_failure for e in failures)


def test_filter_failures_empty_list():
    """filter_failures should return an empty list when given no events."""
    assert filter_failures([]) == []


def test_to_dict_contains_expected_keys():
    event = parse_line(SAMPLE_CMD_LINE)
    assert event is not None
    d = event.to_dict()
    assert set(d.keys()) == {"timestamp", "host", "pid", "message", "job_name", "is_failure"}


def test_to_dict_values_match_event():
    """to_dict values should match the corresponding event attributes."""
    event = parse_line(SAMPLE_CMD_LINE)
    assert event is not None
    d = event.to_dict()
    assert d["host"] == event.host
    assert d["pid"] == event.pid
    assert d["job_name"] == event.job_name
    assert d["is_failure"] == event.is_failure


def test_parse_log_file(tmp_path):
    log_file = tmp_path / "cron.log"
    log_file.write_text(
        "\n".join([SAMPLE_CMD_LINE, SAMPLE_ERROR_LINE, NON_CRON_LINE, ""])
    )
    events = parse_log_file(str(log_file))
    assert len(events) == 2


def test_parse_log_file_missing_raises():
    with pytest.raises(FileNotFoundError):
        parse_log_file("/nonexistent/path/cron.log")
