"""Parse cron job execution logs and detect failures."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


CRON_LOG_PATTERN = re.compile(
    r"(?P<timestamp>\w+\s+\d+\s+[\d:]+)\s+"
    r"(?P<host>\S+)\s+CRON\[(?P<pid>\d+)\]:\s+"
    r"(?P<message>.+)"
)

FAILURE_KEYWORDS = ["error", "failed", "failure", "exit status", "no such file"]


@dataclass
class CronEvent:
    timestamp: str
    host: str
    pid: str
    message: str
    job_name: Optional[str] = None
    is_failure: bool = False
    raw_line: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "host": self.host,
            "pid": self.pid,
            "message": self.message,
            "job_name": self.job_name,
            "is_failure": self.is_failure,
        }


def parse_line(line: str) -> Optional[CronEvent]:
    """Parse a single syslog cron line into a CronEvent."""
    match = CRON_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    message = match.group("message")
    is_failure = any(kw in message.lower() for kw in FAILURE_KEYWORDS)

    job_name = None
    job_match = re.search(r"CMD\s+\((.+?)\)", message)
    if job_match:
        job_name = job_match.group(1).strip()

    return CronEvent(
        timestamp=match.group("timestamp"),
        host=match.group("host"),
        pid=match.group("pid"),
        message=message,
        job_name=job_name,
        is_failure=is_failure,
        raw_line=line.strip(),
    )


def parse_log_file(path: str) -> list[CronEvent]:
    """Read a log file and return all parsed CronEvents."""
    events: list[CronEvent] = []
    try:
        with open(path, "r") as f:
            for line in f:
                event = parse_line(line)
                if event is not None:
                    events.append(event)
    except OSError as e:
        raise OSError(f"Could not read log file '{path}': {e}") from e
    return events


def filter_failures(events: list[CronEvent]) -> list[CronEvent]:
    """Return only events that are failures."""
    return [e for e in events if e.is_failure]


def group_by_job(events: list[CronEvent]) -> dict[str, list[CronEvent]]:
    """Group events by job name.

    Events without a detected job name are grouped under the key None.
    """
    groups: dict[str, list[CronEvent]] = {}
    for event in events:
        key = event.job_name
        groups.setdefault(key, []).append(event)
    return groups
