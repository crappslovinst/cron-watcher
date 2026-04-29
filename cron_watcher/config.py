"""Configuration loading and validation for cron-watcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class AlertConfig:
    webhook_url: str | None = None
    email_to: list[str] = field(default_factory=list)
    email_from: str = "cron-watcher@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25


@dataclass
class HealthCheckConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class Config:
    log_file: str
    poll_interval: float = 5.0
    report_interval: int = 0  # seconds; 0 = disabled
    top_n: int = 5
    alert: AlertConfig = field(default_factory=AlertConfig)
    healthcheck: HealthCheckConfig = field(default_factory=HealthCheckConfig)


def _parse_alert(raw: dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        webhook_url=raw.get("webhook_url"),
        email_to=raw.get("email_to", []),
        email_from=raw.get("email_from", "cron-watcher@localhost"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
    )


def _parse_healthcheck(raw: dict[str, Any]) -> HealthCheckConfig:
    return HealthCheckConfig(
        enabled=bool(raw.get("enabled", False)),
        host=raw.get("host", "127.0.0.1"),
        port=int(raw.get("port", 8765)),
    )


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    if "log_file" not in raw:
        raise ValueError("Config must specify 'log_file'")

    alert_cfg = _parse_alert(raw.get("alert", {}))
    hc_cfg = _parse_healthcheck(raw.get("healthcheck", {}))

    return Config(
        log_file=raw["log_file"],
        poll_interval=float(raw.get("poll_interval", 5.0)),
        report_interval=int(raw.get("report_interval", 0)),
        top_n=int(raw.get("top_n", 5)),
        alert=alert_cfg,
        healthcheck=hc_cfg,
    )
