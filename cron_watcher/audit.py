"""Audit log: append-only record of every alert dispatched by cron-watcher."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cron_watcher.log_parser import CronEvent


@dataclass
class AuditEntry:
    timestamp: str
    alert_type: str          # "webhook" | "email" | "digest"
    job_names: List[str]
    failure_count: int
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "alert_type": self.alert_type,
            "job_names": self.job_names,
            "failure_count": self.failure_count,
            "success": self.success,
            "error": self.error,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_entry(
    alert_type: str,
    events: List[CronEvent],
    success: bool,
    error: Optional[str] = None,
) -> AuditEntry:
    job_names = sorted({e.job for e in events if e.job})
    return AuditEntry(
        timestamp=_now_iso(),
        alert_type=alert_type,
        job_names=job_names,
        failure_count=len(events),
        success=success,
        error=error,
    )


def append_entry(log_path: Path, entry: AuditEntry) -> None:
    """Append a single JSON line to the audit log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.to_dict()) + "\n")


def read_entries(log_path: Path) -> List[AuditEntry]:
    """Read all entries from the audit log; skip corrupt lines."""
    if not log_path.exists():
        return []
    entries: List[AuditEntry] = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                entries.append(AuditEntry(**d))
            except Exception:
                pass
    return entries
