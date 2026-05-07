"""Per-job alert cooldown tracker.

Prevents alert fatigue by enforcing a minimum gap between successive
alerts for the same cron job.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CooldownConfig:
    enabled: bool = True
    # seconds between alerts for the same job
    period: int = 300


def cooldown_config_from_dict(d: dict) -> CooldownConfig:
    raw = d.get("cooldown", {})
    return CooldownConfig(
        enabled=bool(raw.get("enabled", True)),
        period=int(raw.get("period", 300)),
    )


@dataclass
class CooldownState:
    # job_name -> timestamp of last alert
    _last_alert: Dict[str, float] = field(default_factory=dict)

    def is_cooled_down(self, job: str, now: Optional[float] = None) -> bool:
        """Return True if enough time has passed since the last alert."""
        ts = self._last_alert.get(job)
        if ts is None:
            return True
        return (now or time.monotonic()) - ts >= 0

    def check_and_record(
        self,
        job: str,
        config: CooldownConfig,
        now: Optional[float] = None,
    ) -> bool:
        """Return True (and record) if the alert should proceed; False if suppressed."""
        if not config.enabled:
            return True
        t = now or time.monotonic()
        last = self._last_alert.get(job)
        if last is not None and (t - last) < config.period:
            return False
        self._last_alert[job] = t
        return True

    def reset_job(self, job: str) -> None:
        self._last_alert.pop(job, None)

    def reset_all(self) -> None:
        self._last_alert.clear()
