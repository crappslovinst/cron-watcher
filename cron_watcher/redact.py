"""Redact sensitive values from cron job command strings before logging or alerting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# Patterns that look like secrets: env-style assignments, flags with values, tokens
_DEFAULT_PATTERNS: List[str] = [
    r"(?i)(password|passwd|secret|token|api[_-]?key|auth)[=:\s]+\S+",
    r"(?i)(--password|--secret|--token|--key)\s+\S+",
    r"[A-Za-z0-9+/]{32,}={0,2}",  # base64-ish blobs
]

_REPLACEMENT = "[REDACTED]"


@dataclass
class RedactConfig:
    enabled: bool = True
    extra_patterns: List[str] = field(default_factory=list)


def redact_config_from_dict(d: dict) -> RedactConfig:
    raw = d.get("redact", {})
    return RedactConfig(
        enabled=bool(raw.get("enabled", True)),
        extra_patterns=list(raw.get("extra_patterns", [])),
    )


def _compile_patterns(cfg: RedactConfig) -> List[re.Pattern]:
    patterns = list(_DEFAULT_PATTERNS) + list(cfg.extra_patterns)
    return [re.compile(p) for p in patterns]


def redact(text: str, cfg: RedactConfig | None = None) -> str:
    """Return *text* with sensitive substrings replaced by [REDACTED]."""
    if cfg is None:
        cfg = RedactConfig()
    if not cfg.enabled:
        return text
    result = text
    for pattern in _compile_patterns(cfg):
        result = pattern.sub(_REPLACEMENT, result)
    return result


def redact_event_command(command: str, cfg: RedactConfig | None = None) -> str:
    """Convenience wrapper used by other modules."""
    return redact(command, cfg)
