"""Configuration loading for cron-watcher."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AlertConfig:
    webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    email_from: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25


@dataclass
class HealthCheckConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8080


@dataclass
class Config:
    log_file: str
    poll_interval: int = 10
    report_interval: int = 0
    state_file: str = "/tmp/cron_watcher.state"
    alert: AlertConfig = field(default_factory=AlertConfig)
    healthcheck: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    filter: dict = field(default_factory=dict)


def _parse_alert(raw: dict) -> AlertConfig:
    return AlertConfig(
        webhook_url=raw.get("webhook_url"),
        email_to=raw.get("email_to"),
        email_from=raw.get("email_from"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
    )


def _parse_healthcheck(raw: dict) -> HealthCheckConfig:
    return HealthCheckConfig(
        enabled=raw.get("enabled", False),
        host=raw.get("host", "127.0.0.1"),
        port=int(raw.get("port", 8080)),
    )


def load_config(path: str | Path) -> Config:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with p.open("rb") as fh:
        raw = tomllib.load(fh)

    alert = _parse_alert(raw.get("alert", {}))
    healthcheck = _parse_healthcheck(raw.get("healthcheck", {}))
    filter_cfg = raw.get("filter", {})

    return Config(
        log_file=raw["log_file"],
        poll_interval=int(raw.get("poll_interval", 10)),
        report_interval=int(raw.get("report_interval", 0)),
        state_file=raw.get("state_file", "/tmp/cron_watcher.state"),
        alert=alert,
        healthcheck=healthcheck,
        filter=filter_cfg,
    )
