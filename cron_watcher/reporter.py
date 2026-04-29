"""Generates summary reports from cron failure events."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cron_watcher.log_parser import CronEvent


@dataclass
class Report:
    generated_at: str
    total_failures: int
    unique_jobs: int
    top_failing_jobs: List[dict]
    events: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "total_failures": self.total_failures,
            "unique_jobs": self.unique_jobs,
            "top_failing_jobs": self.top_failing_jobs,
            "events": self.events,
        }


def build_report(
    events: List[CronEvent],
    top_n: int = 5,
    generated_at: Optional[str] = None,
) -> Report:
    """Build a summary report from a list of failure events."""
    if generated_at is None:
        generated_at = datetime.utcnow().isoformat() + "Z"

    job_counts: Counter = Counter()
    for event in events:
        label = event.command or event.raw
        job_counts[label] += 1

    top_failing = [
        {"job": job, "failures": count}
        for job, count in job_counts.most_common(top_n)
    ]

    return Report(
        generated_at=generated_at,
        total_failures=len(events),
        unique_jobs=len(job_counts),
        top_failing_jobs=top_failing,
        events=[_event_summary(e) for e in events],
    )


def _event_summary(event: CronEvent) -> dict:
    return {
        "timestamp": event.timestamp,
        "job": event.command or event.raw,
        "exit_code": event.exit_code,
        "message": event.message,
    }


def format_text_report(report: Report) -> str:
    """Render a human-readable text version of the report."""
    lines = [
        f"Cron Watcher Report — {report.generated_at}",
        f"Total failures : {report.total_failures}",
        f"Unique jobs    : {report.unique_jobs}",
        "",
        "Top failing jobs:",
    ]
    for entry in report.top_failing_jobs:
        lines.append(f"  {entry['failures']:>4}x  {entry['job']}")
    return "\n".join(lines)
