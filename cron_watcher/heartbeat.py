"""Heartbeat module — periodically pings a remote URL to signal the daemon is alive."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatConfig:
    enabled: bool = False
    url: str = ""
    interval_seconds: int = 60
    timeout_seconds: int = 10
    headers: dict = field(default_factory=dict)


def heartbeat_config_from_dict(raw: dict) -> HeartbeatConfig:
    hb = raw.get("heartbeat", {})
    return HeartbeatConfig(
        enabled=bool(hb.get("enabled", False)),
        url=str(hb.get("url", "")),
        interval_seconds=int(hb.get("interval_seconds", 60)),
        timeout_seconds=int(hb.get("timeout_seconds", 10)),
        headers=dict(hb.get("headers", {})),
    )


@dataclass
class HeartbeatState:
    last_ping_ts: Optional[float] = None
    last_ping_ok: Optional[bool] = None
    total_pings: int = 0
    total_failures: int = 0


def ping(cfg: HeartbeatConfig, state: HeartbeatState) -> bool:
    """Send a single heartbeat ping. Returns True on success."""
    if not cfg.enabled or not cfg.url:
        return False

    req = urllib.request.Request(cfg.url, method="GET")
    for k, v in cfg.headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            ok = 200 <= resp.status < 300
    except urllib.error.URLError as exc:
        logger.warning("Heartbeat ping failed: %s", exc)
        ok = False
    except Exception as exc:  # noqa: BLE001
        logger.error("Heartbeat unexpected error: %s", exc)
        ok = False

    state.last_ping_ts = time.time()
    state.last_ping_ok = ok
    state.total_pings += 1
    if not ok:
        state.total_failures += 1
        logger.warning("Heartbeat ping unsuccessful (url=%s)", cfg.url)
    else:
        logger.debug("Heartbeat ping OK (url=%s)", cfg.url)

    return ok


def should_ping(cfg: HeartbeatConfig, state: HeartbeatState) -> bool:
    """Return True if enough time has elapsed since the last ping."""
    if not cfg.enabled or not cfg.url:
        return False
    if state.last_ping_ts is None:
        return True
    return (time.time() - state.last_ping_ts) >= cfg.interval_seconds
