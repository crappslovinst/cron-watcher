import json
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from cron_watcher.alerter import send_webhook, send_email, dispatch_alerts, _build_payload
from cron_watcher.config import AlertConfig
from cron_watcher.log_parser import CronEvent


@pytest.fixture()
def sample_events():
    return [
        CronEvent(
            timestamp=datetime(2024, 1, 15, 3, 0, 0),
            job="/usr/bin/backup.sh",
            message="exit status 1",
            is_failure=True,
            exit_code=1,
        )
    ]


@pytest.fixture()
def alert_cfg():
    return AlertConfig(
        webhook_url="http://hooks.example.com/notify",
        email_to="ops@example.com",
        smtp_host="smtp.example.com",
        smtp_port=25,
        smtp_tls=False,
        smtp_user=None,
        smtp_password=None,
        email_from="cron-watcher@example.com",
    )


def test_build_payload(sample_events):
    payload = _build_payload(sample_events)
    assert payload["count"] == 1
    assert payload["alert"] == "cron-watcher failure report"
    assert len(payload["failures"]) == 1


def test_send_webhook_success(sample_events):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_webhook("http://hooks.example.com/notify", sample_events)

    assert result is True


def test_send_webhook_failure(sample_events):
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = send_webhook("http://hooks.example.com/notify", sample_events)

    assert result is False


def test_send_email_success(alert_cfg, sample_events):
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_email(alert_cfg, sample_events)

    assert result is True


def test_send_email_missing_config(sample_events):
    cfg = AlertConfig(smtp_host=None, email_to=None)
    result = send_email(cfg, sample_events)
    assert result is False


def test_dispatch_alerts_calls_both(alert_cfg, sample_events):
    with patch("cron_watcher.alerter.send_webhook", return_value=True) as wh, \
         patch("cron_watcher.alerter.send_email", return_value=True) as em:
        dispatch_alerts(alert_cfg, sample_events)
        wh.assert_called_once()
        em.assert_called_once()


def test_dispatch_alerts_skips_on_empty(alert_cfg):
    with patch("cron_watcher.alerter.send_webhook") as wh, \
         patch("cron_watcher.alerter.send_email") as em:
        dispatch_alerts(alert_cfg, [])
        wh.assert_not_called()
        em.assert_not_called()
