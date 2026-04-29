import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import List

import urllib.request
import urllib.error

from cron_watcher.config import AlertConfig
from cron_watcher.log_parser import CronEvent, to_dict

logger = logging.getLogger(__name__)


def _build_payload(events: List[CronEvent]) -> dict:
    return {
        "alert": "cron-watcher failure report",
        "failures": [to_dict(e) for e in events],
        "count": len(events),
    }


def send_webhook(url: str, events: List[CronEvent]) -> bool:
    payload = json.dumps(_build_payload(events)).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Webhook delivered, status=%s", resp.status)
            return True
    except urllib.error.URLError as exc:
        logger.error("Webhook delivery failed: %s", exc)
        return False


def send_email(cfg: AlertConfig, events: List[CronEvent]) -> bool:
    if not cfg.email_to or not cfg.smtp_host:
        logger.warning("Email alert requested but smtp_host/email_to not configured")
        return False

    body_lines = ["cron-watcher detected failures:\n"]
    for e in events:
        body_lines.append(
            f"  [{e.timestamp}] job={e.job!r} exit={e.exit_code} msg={e.message!r}"
        )
    body = "\n".join(body_lines)

    msg = MIMEText(body)
    msg["Subject"] = f"[cron-watcher] {len(events)} failure(s) detected"
    msg["From"] = cfg.email_from or "cron-watcher@localhost"
    msg["To"] = cfg.email_to

    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port or 25, timeout=10) as server:
            if cfg.smtp_tls:
                server.starttls()
            if cfg.smtp_user and cfg.smtp_password:
                server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(msg["From"], [cfg.email_to], msg.as_string())
        logger.info("Email alert sent to %s", cfg.email_to)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Email delivery failed: %s", exc)
        return False


def dispatch_alerts(cfg: AlertConfig, events: List[CronEvent]) -> None:
    if not events:
        return
    if cfg.webhook_url:
        send_webhook(cfg.webhook_url, events)
    if cfg.email_to:
        send_email(cfg, events)
