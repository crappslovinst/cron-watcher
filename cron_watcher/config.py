from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import tomllib  # Python 3.11+; falls back to tomli for older versions


@dataclass
class AlertConfig:
    webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    email_from: Optional[str] = "cron-watcher@localhost"
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    smtp_tls: bool = False
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


@dataclass
class Config:
    log_file: str = "/var/log/syslog"
    poll_interval: float = 5.0
    failure_threshold: int = 1
    alert: AlertConfig = field(default_factory=AlertConfig)


def _parse_alert(raw: dict) -> AlertConfig:
    return AlertConfig(
        webhook_url=raw.get("webhook_url"),
        email_to=raw.get("email_to"),
        email_from=raw.get("email_from", "cron-watcher@localhost"),
        smtp_host=raw.get("smtp_host"),
        smtp_port=int(raw.get("smtp_port", 25)),
        smtp_tls=bool(raw.get("smtp_tls", False)),
        smtp_user=raw.get("smtp_user"),
        smtp_password=raw.get("smtp_password"),
    )


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as fh:
        try:
            raw = tomllib.load(fh)
        except AttributeError:
            import tomli as tomllib  # type: ignore
            fh.seek(0)
            raw = tomllib.load(fh)

    alert_cfg = _parse_alert(raw.get("alert", {}))

    return Config(
        log_file=raw.get("log_file", "/var/log/syslog"),
        poll_interval=float(raw.get("poll_interval", 5.0)),
        failure_threshold=int(raw.get("failure_threshold", 1)),
        alert=alert_cfg,
    )
