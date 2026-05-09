"""Envelope wraps outgoing alert payloads with metadata before dispatch."""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cron_watcher.log_parser import CronEvent, to_dict as event_to_dict


@dataclass
class EnvelopeConfig:
    include_hostname: bool = True
    include_timestamp: bool = True
    source_tag: str = "cron-watcher"
    extra_fields: Dict[str, str] = field(default_factory=dict)


def envelope_config_from_dict(raw: Dict[str, Any]) -> EnvelopeConfig:
    section = raw.get("envelope", {})
    return EnvelopeConfig(
        include_hostname=section.get("include_hostname", True),
        include_timestamp=section.get("include_timestamp", True),
        source_tag=section.get("source_tag", "cron-watcher"),
        extra_fields=section.get("extra_fields", {}),
    )


def wrap(events: List[CronEvent], cfg: EnvelopeConfig) -> Dict[str, Any]:
    """Return a dict envelope containing the serialised events plus metadata."""
    payload: Dict[str, Any] = {
        "source": cfg.source_tag,
        "events": [event_to_dict(e) for e in events],
        "event_count": len(events),
    }
    if cfg.include_hostname:
        payload["hostname"] = socket.gethostname()
    if cfg.include_timestamp:
        payload["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if cfg.extra_fields:
        payload["extra"] = dict(cfg.extra_fields)
    return payload
