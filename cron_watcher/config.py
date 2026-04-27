import os
import json
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AlertConfig:
    webhook_url: Optional[str] = None
    email_to: Optional[List[str]] = field(default_factory=list)
    email_from: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25


@dataclass
class Config:
    log_file: str = "/var/log/cron-watcher.log"
    db_path: str = "/var/lib/cron-watcher/jobs.db"
    check_interval: int = 60  # seconds
    alert: AlertConfig = field(default_factory=AlertConfig)
    jobs: List[dict] = field(default_factory=list)


def load_config(path: str) -> Config:
    """Load configuration from a JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = json.load(f)

    alert_data = raw.get("alert", {})
    alert = AlertConfig(
        webhook_url=alert_data.get("webhook_url"),
        email_to=alert_data.get("email_to", []),
        email_from=alert_data.get("email_from"),
        smtp_host=alert_data.get("smtp_host", "localhost"),
        smtp_port=alert_data.get("smtp_port", 25),
    )

    return Config(
        log_file=raw.get("log_file", "/var/log/cron-watcher.log"),
        db_path=raw.get("db_path", "/var/lib/cron-watcher/jobs.db"),
        check_interval=raw.get("check_interval", 60),
        alert=alert,
        jobs=raw.get("jobs", []),
    )
