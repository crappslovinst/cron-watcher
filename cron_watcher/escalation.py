"""Escalation policy: re-alert if a job keeps failing beyond a threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class EscalationConfig:
    enabled: bool = False
    # number of consecutive failures before escalating
    threshold: int = 3
    # cooldown in seconds between escalation alerts for the same job
    cooldown: int = 1800


@dataclass
class _JobEscalationState:
    consecutive_failures: int = 0
    last_escalated_at: Optional[datetime] = None


@dataclass
class EscalationTracker:
    config: EscalationConfig
    _states: Dict[str, _JobEscalationState] = field(default_factory=dict)

    def _get_state(self, job: str) -> _JobEscalationState:
        if job not in self._states:
            self._states[job] = _JobEscalationState()
        return self._states[job]

    def record_failure(self, job: str) -> bool:
        """Record a failure for *job*. Returns True if escalation should fire."""
        if not self.config.enabled:
            return False
        state = self._get_state(job)
        state.consecutive_failures += 1
        if state.consecutive_failures < self.config.threshold:
            return False
        now = datetime.now(tz=timezone.utc)
        if state.last_escalated_at is not None:
            elapsed = (now - state.last_escalated_at).total_seconds()
            if elapsed < self.config.cooldown:
                return False
        state.last_escalated_at = now
        return True

    def record_success(self, job: str) -> None:
        """Reset consecutive failure counter on success."""
        if job in self._states:
            self._states[job].consecutive_failures = 0

    def consecutive_failures(self, job: str) -> int:
        return self._get_state(job).consecutive_failures


def escalation_config_from_dict(raw: dict) -> EscalationConfig:
    return EscalationConfig(
        enabled=bool(raw.get("enabled", False)),
        threshold=int(raw.get("threshold", 3)),
        cooldown=int(raw.get("cooldown", 1800)),
    )
